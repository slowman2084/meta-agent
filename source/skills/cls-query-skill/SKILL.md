---
name: cls-query-skill
description: 腾讯云 CLS 日志智能查询 Skill，支持 Topic 名称自动解析为 TopicID、自然语言查询、自动分页续查。基于 SearchLog API，增强版 cls-query。
metadata: { "openclaw": { "requires": { "env": ["CLS_SECRET_ID", "CLS_SECRET_KEY", "CLS_ENDPOINT", "CLS_REGION"] }, "category": "tencent", "tencentTokenMode": "custom", "tokenUrl": "https://console.cloud.tencent.com/cloudapp/run/yunti/apply-auth", "emoji": "📋" } }
---

# CLS Query Skill (Enhanced)

本 skill 用于查询腾讯云 CLS (Cloud Log Service) 日志，支持检索和分析日志主题中的日志数据。

**相比基础版 cls-query 的增强**：
1. **Topic 名称自动解析**：用户只需提供 Topic 名称（如 "omp-trace-log"），自动查找对应的 TopicID
2. **自动分页续查**：当数据量大时自动使用 Context 分页，直到获取所有结果或达到上限

## 使用场景

- 用 Topic 名称（而非 UUID）查询日志
- 根据 TopicId 查询指定日志主题的日志
- 执行检索分析语句过滤日志
- 分析日志统计数据
- 排查线上问题，检索错误日志
- 大数据量自动分页获取完整结果

## 配置项

本 skill 支持**三级配置**，按以下优先级加载配置值：

```
命令行参数（--secret-id 等）  >  环境变量（CLS_SECRET_ID 等）  >  .env 文件  >  内置默认值
```

| 优先级 | 配置方式 | 说明 |
|--------|----------|------|
| 🥇 最高 | 命令行参数 | 通过 `--secret-id`、`--secret-key` 等参数显式传入 |
| 🥈 其次 | 环境变量 | 通过 `export CLS_SECRET_ID=xxx` 等方式设置 |
| 🥉 再次 | `.env` 文件 | 使用 `python-dotenv` 自动加载当前目录或 skill 根目录下的 `.env` 文件 |
| ⬜ 最低 | 内置默认值 | 仅 `endpoint` 和 `region` 有默认值 |

> **提示**：三种配置方式可混合使用。例如将密钥写入 `.env` 文件，运行时仅通过命令行传入 `--topic-id` 和 `--query` 等查询参数即可。

### 配置参数列表

| 配置项 | 命令行参数 | 环境变量 | 必填 | 默认值 | 说明 |
|--------|-----------|----------|------|--------|------|
| SecretId | `--secret-id` | `CLS_SECRET_ID` | ✅ 是 | — | 腾讯云 API 访问密钥 ID |
| SecretKey | `--secret-key` | `CLS_SECRET_KEY` | ✅ 是 | — | 腾讯云 API 访问密钥 KEY |
| Endpoint | `--endpoint` | `CLS_ENDPOINT` | 否 | `cls.internal.tencentcloudapi.com` | CLS 服务端点域名 |
| Region | `--region` | `CLS_REGION` | 否 | `ap-guangzhou` | CLS 服务地域 |

### 如何获取 Secret ID 和 Secret Key

如果你还没有腾讯云 API 密钥（SecretId / SecretKey），请通过以下地址申请：

👉 **[申请 CLS API 访问权限](https://console.cloud.tencent.com/cloudapp/run/yunti/apply-auth)**

申请完成后，将获取到的 `SecretId` 和 `SecretKey` 通过以下任意方式配置。

### 配置方式一：使用 .env 文件（推荐）

在 skill 根目录或当前工作目录下创建 `.env` 文件：

```bash
# .env
CLS_SECRET_ID=your_secret_id
CLS_SECRET_KEY=your_secret_key
CLS_ENDPOINT=cls.internal.tencentcloudapi.com
CLS_REGION=ap-guangzhou
```

> 需安装 `python-dotenv`：`pip install python-dotenv`（未安装时会静默跳过 `.env` 加载）

### 配置方式二：使用环境变量

```bash
export CLS_SECRET_ID="your_secret_id"
export CLS_SECRET_KEY="your_secret_key"
export CLS_ENDPOINT="cls.internal.tencentcloudapi.com"  # 内网（推荐）
export CLS_REGION="ap-guangzhou"
```

### 配置方式三：命令行参数

```bash
python scripts/cls_query.py \
  --secret-id "your_secret_id" \
  --secret-key "your_secret_key" \
  --endpoint "cls.internal.tencentcloudapi.com" \
  --region "ap-guangzhou" \
  ...
```

### Endpoint 说明

| 域名 | 用途 | 场景 |
|------|------|------|
| `cls.tencentcloudapi.com` | 外网 API | 公网调用 |
| `cls.internal.tencentcloudapi.com` | 内网 API | VPC 内网/腾讯云环境调用（推荐） |
| `ap-guangzhou.cls.tencentyun.com` | 日志上报 | 日志写入/上报（不是 API 调用） |

**注意**：如果 SecretId 只开启了内网权限，必须使用 `cls.internal.tencentcloudapi.com`

## 输入参数

用户调用时需提供以下参数：

| 参数 | 必选 | 类型 | 说明 |
|------|------|------|------|
| topic_id | 是 | string | 日志主题 ID (TopicId) |
| query | 是 | string | 检索分析语句，最大 12KB，由 `[检索条件] \| [SQL语句]` 构成 |
| from | 是 | int64 | 起始时间，Unix 时间戳（毫秒） |
| to | 是 | int64 | 结束时间，Unix 时间戳（毫秒） |
| limit | 否 | int | 返回日志条数，默认 100，最大 1000 |
| sort | 否 | string | 排序方式，`asc` 升序 或 `desc` 降序，默认 `desc` |
| highlight | 否 | bool | 是否高亮关键词，默认 false |
| use_new_analysis | 否 | bool | 是否使用新的分析结果格式，默认 true |
| syntax_rule | 否 | int | 检索语法，0-Lucene 或 1-CQL（推荐），默认 1 |

## 检索语法示例

### 基础检索
```
http_code:200                    # 检索 HTTP 状态码为 200 的日志
level:error                      # 检索错误级别日志
"登录失败"                        # 全文检索包含指定关键词的日志
```

### 组合检索
```
http_code:500 AND method:POST    # 检索 POST 请求且状态码 500 的日志
level:error OR level:warn        # 检索错误或警告日志
```

### 统计分析
```
level:error | SELECT count(*) AS error_count, url GROUP BY url LIMIT 10
```
检索错误日志并按 url 分组统计数量，返回前 10 条。

## 调用流程

1. **解析用户意图**：从自然语言中提取 Topic、时间范围、查询目标
2. **Topic 解析**：名称 → TopicID（参见增强功能 1）
3. **加载配置**：从 skill 配置或环境变量获取 SecretId、SecretKey、Endpoint、Region
4. **构建请求**：根据输入参数构建 SearchLog API 请求
5. **签名计算**：使用 TC3-HMAC-SHA256 签名算法（参考 references/cls_api.md）
6. **发送请求**：调用 CLS SearchLog API
7. **解析结果**：解析返回的日志数据或统计分析结果
8. **格式化输出**：按输出规范格式化（参见下方输出规范）

---

## 查询构建规则（关键）

### "报错"/"错误"的统计口径

当用户要求查询"报错"、"错误"、"异常"相关的接口/请求时：

**必须基于 HTTP 状态码统计，而非日志级别或 msg 字段。** 具体口径：
- HTTP 4xx（400, 401, 403, 404, 429 等）= 客户端错误
- HTTP 5xx（500, 502, 503, 504 等）= 服务端错误
- null/空状态码 = 连接失败或无响应

正确查询示例：
```sql
-- 所有非 2xx 状态码的接口统计
* | SELECT url, status, count(*) as error_count 
  WHERE status >= 400 OR status IS NULL
  GROUP BY url, status 
  ORDER BY error_count DESC 
  LIMIT 20
```

错误做法（禁止）：
```sql
-- ❌ 仅查 level:error（遗漏 HTTP 层面的错误）
level:error | SELECT url, count(*) as cnt GROUP BY url
-- ❌ 仅查 status:500（遗漏 4xx 和 null）
status:500 | SELECT url, count(*) as cnt GROUP BY url
```

### 查询降级策略

当 SQL 查询超时或报错时，按以下顺序降级：

1. **精确函数 → 近似函数**
   - `COUNT(DISTINCT x)` → `APPROX_DISTINCT(x)`（HyperLogLog，误差 ≤5%）
   - 降级时必须在输出中标注"⚠️ 估算值，基于 HyperLogLog 近似计算，误差 ≤5%"

2. **缩小时间窗口（保持原始问题的回答完整性）**
   - 3天 → 1天 → 6小时 → 1小时
   - **关键**：缩小窗口后，必须尝试用多个窗口的结果拼接或外推回答原始问题
   - 例如：用户问"最近 3 天有多少 distinct instance_id"，如果 3 天超时但 1 天成功：
     - 分别查询每天的数据（day1, day2, day3）
     - 或查 1 天后说明"最近 1 天有 X 个，3 天数据因数据量过大超时，建议分天查询"
   - **禁止**：仅返回缩小窗口的结果而不说明与原始问题的差距

3. **降低复杂度**
   - 多字段 GROUP BY → 单字段 GROUP BY
   - 嵌套子查询 → 拆分为多次简单查询

4. **降低数据量**
   - LIMIT 1000 → LIMIT 100
   - 去掉非必要的 ORDER BY

5. **分段查询后合并**（适用于大时间范围超时场景）
   - 将大时间范围拆分为多个小段（如 3 天拆为 3 个 1 天）
   - 分别查询后合并结果
   - 对于 DISTINCT 计数类查询，分段结果取并集（可能有重叠，说明"实际去重数 ≤ 分段之和"）

**每次降级都必须告知用户降级原因和影响。首句仍然直接回答用户问题（即使是降级后的近似答案）。**

---

## 输出格式

### 输出规范（必须遵守）

1. **首句直接回答用户问题的核心数字/结论**。例如：
   - "最近 1 天共有 **5 个接口**报错，Top 1 为 /api/xxx（1,163 次 401 错误）"
   - "最近 3 天共有约 **65,733 个**不同的 instance_id 在上报数据（⚠️ HyperLogLog 近似值）"
   - 禁止以"查询结果："、"根据分析"、"报告标题" 等铺垫开场
2. **核心结论置顶** → 数据/证据居中 → 下一步建议收尾
3. **统计结果必须使用 Markdown 表格**，默认收敛到 Top 5（用户要求更多时再展开），至少包含：主维度、数量、辅助判断列
4. **时间戳必须转换为可读格式**（如 "2026-04-09 12:00:00"），禁止在正文和查询过程中暴露裸毫秒时间戳。查询过程中记录的 from/to 也必须同时标注可读时间。
5. **存在头部异常时**，用"⚠️ 异常项"单独点出，并补充至少 1 条规律判断（时间段/实例/状态码维度）
6. **以"下一步"收尾**，给出具体的下钻建议，必须涵盖：按接口路径（`request`/`uri`/`url`）下钻 + 按时段下钻。主动询问"是否继续下钻？"
7. **审慎表述**：对异常原因使用"可能"、"建议排查"等措辞，区分事实结论与推测假设。禁止对未经验证的原因断言。
8. **状态码分类**：涉及 HTTP 状态码时，必须读取 `references/http_status_codes.md` 确保分类正确。特别注意：101 是信息性响应（非错误），499 是客户端主动断开（非服务端错误）。
9. **查询过程透明化**：在输出末尾附加「查询过程」小节，记录每次 API 调用的关键参数。from/to 必须同时标注可读时间。格式：

```markdown
## 查询过程
1. Topic 定位: "omp-trace-log" → 310ded45-... (精确匹配 references/topic_mapping.csv)
2. 时间转换: "最近1天" → 2026-04-08 16:00 ~ 2026-04-09 16:00 (from: 1744091234000, to: 1744177634000)
3. 查询 1: `* | SELECT url, status, count(*)... WHERE status>=400` → 成功, 7 条结果
4. (若有降级) 查询 2: 缩小窗口/改用近似函数 → ...
```

### API 原始返回格式

检索原始日志返回：
```json
{
  "Context": "xxx",
  "ListOver": false,
  "Analysis": false,
  "Results": [
    {
      "Time": 1679902806070,
      "TopicId": "xxx",
      "LogJson": "{\"field1\":\"value1\", \"field2\":\"value2\"}"
    }
  ],
  "RequestId": "xxx"
}
```

统计分析返回：
```json
{
  "Analysis": true,
  "AnalysisRecords": ["{\"error_count\":100,\"url\":\"/api/test\"}"],
  "Columns": [{"name":"error_count","type":"long"}, {"name":"url","type":"varchar"}],
  "RequestId": "xxx"
}
```

## 使用示例

### 示例 1：查询错误日志
```
查询 CDN 日志中最近 1 小时的错误日志
topic_id: 601c2a87-ca8e-49c9-xxxx-27286a970db5
query: level:error
from: 1705737600000
to: 1705741200000
limit: 50
```

### 示例 2：统计分析
```
统计最近 24 小时内各 HTTP 状态码的数量
topic_id: xxx
query: * | SELECT http_code, count(*) AS count GROUP BY http_code ORDER BY count DESC
from: 1705651200000
to: 1705737600000
```

## 注意事项

1. 单个日志主题查询并发不能超过 15
2. API 返回数据包最大限制为 49MB，建议启用 gzip 压缩
3. 默认频率限制 10000次/秒
4. 使用 Context 可实现分页获取更多日志（最多 1 万条）
5. 推荐使用 CQL 语法（syntax_rule=1）

---

## 增强功能 1：Topic 名称自动解析

当用户提供的是 Topic **名称**（如 "omp-trace-log"、"d.qq.com-clb-prod"）而非 UUID 格式的 TopicID 时，自动从 Topic 映射表中查找对应的 TopicID。

### 解析流程

1. 判断用户输入是否为 UUID 格式（`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）
   - 是 → 直接作为 topic_id 使用
   - 否 → 进入名称解析
2. 读取 Topic 映射文件：`references/topic_mapping.csv`（若存在）
3. 在映射表的 `topic_name` 列中匹配用户输入（支持模糊匹配）
4. 匹配规则（优先级从高到低）：
   - 精确匹配：`topic_name == 用户输入`
   - 前缀匹配：`topic_name.startswith(用户输入)`
   - 包含匹配：`用户输入 in topic_name`
5. 若匹配到唯一结果 → 使用该 topic_id
6. 若匹配到多个 → 列出候选项让用户确认
7. 若无匹配 → 提示用户提供 TopicID

### Topic 映射表格式

`references/topic_mapping.csv`：
```csv
topic_id,topic_name,search_keyword,region
310ded45-de57-4284-9290-24b49e2708d0,omp-trace-log,trace,ap-guangzhou
42c164f7-1ee9-45fa-b40a-19f9d3f889d6,d.qq.com-clb-prod,clb,ap-guangzhou
...
```

### 使用示例

用户说："帮我查一下 omp-trace-log 最近1天的错误日志"
→ 自动解析 "omp-trace-log" → topic_id = `310ded45-de57-4284-9290-24b49e2708d0`
→ 构建查询并执行

---

## 增强功能 2：自动分页续查

当查询结果未返回完毕（`ListOver == false`）时，自动使用返回的 `Context` 值发起后续查询，直到获取所有结果或达到上限。

### 分页流程

1. 发起首次查询，获取结果
2. 检查响应中的 `ListOver` 字段：
   - `true` → 所有结果已返回，结束
   - `false` → 还有更多数据
3. 取响应中的 `Context` 值，作为下一次查询的 `context` 参数
4. 重复查询，直到：
   - `ListOver == true`（数据获取完毕）
   - 累计获取记录数达到 `max_records`（默认 10000，可配置）
   - 查询次数达到 `max_pages`（默认 10 页，防止无限循环）
5. 合并所有页的结果返回

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--auto-page` | flag | false | 启用自动分页 |
| `--max-records` | int | 10000 | 最大获取记录数 |
| `--max-pages` | int | 10 | 最大查询页数 |

### 使用示例

```bash
python scripts/cls_query.py \
  --topic-id 310ded45-de57-4284-9290-24b49e2708d0 \
  --query "level:error" \
  --from 1705651200000 \
  --to 1705737600000 \
  --auto-page \
  --max-records 5000
```

### 注意

- 自动分页仅对**原始日志检索**生效（`Analysis == false`）
- 统计分析查询（`Analysis == true`）单次即返回完整结果，无需分页
- 每页之间有 100ms 间隔，避免触发频率限制

---

## 错误处理

常见错误码：
- `ResourceNotFound.TopicNotExist`: 日志主题不存在
- `FailedOperation.SyntaxError`: 查询语句解析错误
- `FailedOperation.SearchTimeout`: 查询超时
- `LimitExceeded.LogSearch`: 并发查询超过限制

遇到错误时返回错误码和错误信息，供用户排查。
