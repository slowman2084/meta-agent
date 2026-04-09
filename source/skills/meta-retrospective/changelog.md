## [创建] 初始版本（迁移至 source 目录）

**创建时间：** 2026-03-04
**创建方式：** 从 .codebuddy/agents/iteration-retrospective.md 迁移，同步创建 source 目录
**变更说明：**
- 将原先分散在三个 IDE agents 目录的 prompt 统一到 source 管理
- 重构输入参数接口，适配 evo_looper 的 bak/ + tmp/evalooper/ 目录结构
- 增加第 13 种反模式：优化方向单一（连续 3+ 轮同一方向修改）
- 新增 `forced_new_directions` 输出字段：包含 avoided_directions 和 suggested_directions
- Markdown 报告增加第七节"下轮优化方向建议"
- 分析流程（Phase 3）从依赖 execution_log.txt 改为优先读取 评估报告.md
- 保存位置改为 `source/[AgentName]/tmp/evalooper/iter_[N]/` 目录

## [手动] 职责收窄 v4.0

**时间：** 2026-03-12
**变更说明：**
- 删除 Phase 2b（评估体系质量分析）及 `calibration_diagnostics` 输出字段
- 三元组一致性诊断（rubric/理想态/提示词矛盾）移交新建的 `meta-debug` agent
- `bak_dir` 改为必传参数（无迭代历史则拒绝执行，避免空转）
- 删除 `testcases_yaml_path` 和 `ideal_state_path` 输入参数
- 职责聚焦：专注多轮迭代历史分析、反模式识别、劣化主线归纳、`forced_new_directions` 输出
