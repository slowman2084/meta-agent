# cls-query

腾讯云 CLS (Cloud Log Service) 日志查询 skill，基于腾讯云 SearchLog API 实现检索分析日志功能。

## 基本信息

| 项目 | 内容 |
|------|------|
| **名称** | cls-query |
| **版本** | 1.0.0 |
| **作者** | CodeBuddy |
| **依赖** | Python 3.6+, requests |

## 适用场景

- 腾讯云 CLS 日志检索查询
- 线上问题排查，错误日志分析
- 日志数据统计分析
- 批量日志导出

## 功能特性

- 支持检索和分析日志主题中的日志数据
- 支持原始日志查询和 SQL 统计分析
- 支持 CQL 和 Lucene 两种检索语法
- 支持分页获取更多日志
- 支持结果高亮显示

## 快速开始

### 1. 配置（三级配置支持）

本 skill 支持**三级配置**，按以下优先级加载：

```
命令行参数  >  环境变量  >  .env 文件  >  内置默认值
```

#### 配置参数列表

| 配置项 | 命令行参数 | 环境变量 | 必填 | 默认值 | 说明 |
|--------|-----------|----------|------|--------|------|
| SecretId | `--secret-id` | `CLS_SECRET_ID` | ✅ 是 | — | 腾讯云 API 访问密钥 ID |
| SecretKey | `--secret-key` | `CLS_SECRET_KEY` | ✅ 是 | — | 腾讯云 API 访问密钥 KEY |
| Endpoint | `--endpoint` | `CLS_ENDPOINT` | 否 | `cls.internal.tencentcloudapi.com` | CLS 服务端点域名 |
| Region | `--region` | `CLS_REGION` | 否 | `ap-guangzhou` | CLS 服务地域 |

#### 如何获取 Secret ID 和 Secret Key

如果你还没有腾讯云 API 密钥（SecretId / SecretKey），请通过以下地址申请：

👉 **[申请 CLS API 访问权限](https://console.cloud.tencent.com/cloudapp/run/yunti/apply-auth)**

申请完成后，选择以下任意一种方式配置。

#### 方式一：使用 .env 文件（推荐）

在 skill 根目录或当前工作目录下创建 `.env` 文件：

```bash
# .env
CLS_SECRET_ID=your_secret_id
CLS_SECRET_KEY=your_secret_key
CLS_ENDPOINT=cls.internal.tencentcloudapi.com
CLS_REGION=ap-guangzhou
```

> 需安装 `python-dotenv`：`pip install python-dotenv`（未安装时静默跳过 `.env` 加载）

#### 方式二：使用环境变量

```bash
export CLS_SECRET_ID="your_secret_id"
export CLS_SECRET_KEY="your_secret_key"
export CLS_ENDPOINT="cls.internal.tencentcloudapi.com"  # 内网（推荐）
export CLS_REGION="ap-guangzhou"
```

#### 方式三：命令行参数

```bash
python scripts/cls_query.py \
  --secret-id "your_secret_id" \
  --secret-key "your_secret_key" \
  --endpoint "cls.internal.tencentcloudapi.com" \
  --region "ap-guangzhou" \
  ...
```

> ⚠️ **注意**：如果 SecretId 只开启了内网权限，必须使用 `cls.internal.tencentcloudapi.com`
>
> 💡 **提示**：三种配置方式可混合使用，例如将密钥写入 `.env` 文件，运行时仅传入查询参数即可。

### 2. 使用方式

#### 方式一：直接调用 Python 脚本

```bash
python scripts/cls_query.py \
  --secret-id $CLS_SECRET_ID \
  --secret-key $CLS_SECRET_KEY \
  --topic-id "your_topic_id" \
  --query "level:error" \
  --from 1705737600000 \
  --to 1705741200000 \
  --limit 50
```

#### 方式二：通过 Skill 调用

在 CodeBuddy IDE 中，直接描述你的查询需求，例如：

```
查询最近1小时 CDN 日志中所有错误级别的日志
topic_id: xxx
```

## 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| topic_id | 是 | 日志主题 ID |
| query | 是 | 检索分析语句 |
| from | 是 | 起始时间（毫秒） |
| to | 是 | 结束时间（毫秒） |
| limit | 否 | 返回条数（默认100） |
| sort | 否 | 排序方式（默认desc） |

## 检索示例

### 基础检索

```
# 查询错误日志
level:error

# 查询 HTTP 200 响应
http_code:200

# 全文检索
"登录失败"
```

### 组合检索

```
# AND 组合
level:error AND method:POST

# OR 组合
level:error OR level:warn
```

### 统计分析

```
# 统计 HTTP 状态码分布
* | SELECT http_code, count(*) AS count GROUP BY http_code

# 统计最频繁的请求
* | SELECT url, count(*) AS pv GROUP BY url ORDER BY pv DESC LIMIT 10

# 统计平均响应时间
* | SELECT avg(response_time) AS avg_rt
```

## 使用示例

### 示例 1：查询错误日志

```bash
python scripts/cls_query.py \
  --secret-id "AKIDxxx" \
  --secret-key "xxx" \
  --region "ap-guangzhou" \
  --topic-id "6d64ae25-7fde-4026-9c34-8c1c0b1c42b4" \
  --query "level:error" \
  --from 1704038400000 \
  --to 1706726400000 \
  --limit 50
```

### 示例 2：统计分析 HTTP 状态码

```bash
python scripts/cls_query.py \
  --secret-id "AKIDxxx" \
  --secret-key "xxx" \
  --region "ap-guangzhou" \
  --topic-id "your_topic_id" \
  --query "* | SELECT http_code, count(*) AS count GROUP BY http_code ORDER BY count DESC LIMIT 10" \
  --from 1704038400000 \
  --to 1706726400000
```

### 示例 3：高亮显示关键词

```bash
python scripts/cls_query.py \
  --secret-id "AKIDxxx" \
  --secret-key "xxx" \
  --region "ap-guangzhou" \
  --topic-id "your_topic_id" \
  --query "error" \
  --from 1704038400000 \
  --to 1706726400000 \
  --highlight \
  --limit 20
```

## 目录结构

```
cls-query/
├── SKILL.md              # Skill 定义文件
├── README.md             # 使用说明
├── scripts/
│   └── cls_query.py      # Python 执行脚本
└── references/
    └── cls_api.md        # API 详细文档
```

## 相关文档

- [腾讯云 CLS 官方文档](https://cloud.tencent.com/document/product/614)
- [SearchLog API 文档](https://cloud.tencent.com/document/product/614/56447)
- [CQL 语法说明](https://cloud.tencent.com/document/product/614/44076)
