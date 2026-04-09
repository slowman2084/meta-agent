# cls-query Skill 理想态

## 触发准确性（Trigger Accuracy）

- 当用户请求中包含"查询日志"、"CLS"、"日志检索"、"日志分析"等关键词时，准确触发本 Skill
- 当用户请求与日志查询无关时，不误触发

## 工作流效率（Workflow Efficiency）

- 正确加载配置（.env / 环境变量 / 命令行参数三级优先级）
- 使用正确的 TC3-HMAC-SHA256 签名算法构建请求
- 合理设置查询参数（时间范围、返回条数、排序方式等）

## 执行成功率（Execution Success）

- API 调用成功完成，无签名错误或参数错误
- 遇到错误时返回清晰的错误码和排查建议（如 TopicNotExist、SyntaxError、SearchTimeout）
- 正确处理分页（Context）场景

## 产物质量（Artifact Quality）

- 日志查询结果以结构化格式（表格/JSON）清晰呈现
- 统计分析结果包含完整的列名、类型和数值
- 高亮模式下关键词标注清晰
- 对查询结果提供简要解读或摘要

## 跨会话一致性（Cross-session Consistency）

- 相同查询参数在不同会话中返回一致结果
- 配置加载方式稳定，不因会话切换丢失
