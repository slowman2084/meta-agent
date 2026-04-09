# cls-query-skill 理想态（增强版）

## 触发准确性（Trigger Accuracy）

- 当用户请求中包含"查询日志"、"CLS"、"日志检索"、"日志分析"等关键词时，准确触发本 Skill
- 当用户提供 Topic 名称（非 UUID）时也能正确触发
- 当用户请求与日志查询无关时，不误触发

## Topic 名称解析（Name Resolution）— 新增

- 用户提供 Topic 名称时（如 "omp-trace-log"），能自动查找对应的 TopicID
- 支持精确匹配、前缀匹配、包含匹配
- 匹配多个候选时，列出选项让用户确认
- 无匹配时，给出清晰提示并引导用户提供 TopicID
- Topic 映射表可扩展（references/topic_mapping.csv）

## 工作流效率（Workflow Efficiency）

- 正确加载配置（.env / 环境变量 / 命令行参数三级优先级）
- 使用正确的 TC3-HMAC-SHA256 签名算法构建请求
- 合理设置查询参数（时间范围、返回条数、排序方式等）
- Topic 名称解析过程透明，告知用户解析结果

## 自动分页能力（Auto Pagination）— 新增

- 当 ListOver=false 时，自动使用 Context 续查
- 累计获取记录数可配置（默认上限 10000 条）
- 最大页数可配置（默认 10 页，防止无限循环）
- 分页过程中给出进度提示（"已获取 N 条，继续获取..."）
- 仅对原始日志检索生效，统计分析无需分页

## 执行成功率（Execution Success）

- API 调用成功完成，无签名错误或参数错误
- 遇到错误时返回清晰的错误码和排查建议（如 TopicNotExist、SyntaxError、SearchTimeout）
- 分页过程中单页失败不影响已获取的数据

## 产物质量（Artifact Quality）

- 日志查询结果以结构化格式（表格/JSON）清晰呈现
- 统计分析结果包含完整的列名、类型和数值
- 高亮模式下关键词标注清晰
- 对查询结果提供简要解读或摘要
- 分页结果合并后保持一致的格式

## 跨会话一致性（Cross-session Consistency）

- 相同查询参数在不同会话中返回一致结果
- 配置加载方式稳定，不因会话切换丢失
- Topic 名称映射在不同会话中一致
