## [创建] 初始版本（基于 cls-query 升级）

**创建时间：** 2026-04-09
**创建方式：** 从 cls-query Skill 复制并增强
**增强能力：**
1. Topic 名称自动解析 — 用户提供名称自动查找 TopicID
2. 自动分页续查 — ListOver=false 时自动使用 Context 获取完整结果

**基线参考：** cls-query (207行 SKILL.md, 40条测试用例)
**测试用例数：** 40 条（继承自 cls-query，待补充增强功能用例）

## [优化] iterate 热身完成（4 轮）

**时间：** 2026-04-09
**轮数：** 4 轮（Base → R1 → R2 → R3 → R4）
**分数变化：** 46.8 → 72.8 → 92.7 → 94.4 → **97.5**
**关键改进：**
1. R1: 添加查询构建规则（错误统计口径=HTTP非2xx）+ 降级策略 + 输出规范
2. R2: 增强降级策略（分段查询+合并）+ 输出首句规范（直接给数字）
3. R3: 查询过程透明化（替代 ShareGPT）+ 审慎表述规则
4. R4: 状态码分类下沉到 references/http_status_codes.md + 时间戳全面可读化 + 下钻建议必含 uri 字段
**新增 references：** http_status_codes.md（HTTP 状态码分类与语义）
