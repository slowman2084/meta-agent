#!/usr/bin/env python3
"""
应用校准修复脚本
根据用户决策修改 testcases.yaml 和 prompt.md
"""

import re
import sys

def main():
    # 读取 testcases.yaml
    yaml_path = '/Users/wenxinhuang/Documents/all_in_one/项目/meta-agent/source/cls-log-agent/testcases.yaml'
    with open(yaml_path, 'r') as f:
        content = f.read()
    
    print("开始应用校准修复...")
    
    # DEC2: 修改 case_34 的 TextToSearchLogQuery criterion
    old_34 = "在构建包含 collect_list 或 array_agg 等聚合函数的查询语句前，调用了 TextToSearchLogQuery 工具将语义转为标准检索语法，而非直接拼接函数字符串。"
    new_34 = "构造了有效的聚合查询语句（通过 TextToSearchLogQuery 生成或 Agent 自行手写有效 CLS SQL 均视为合格）。注：简单 GROUP BY + COUNT 场景允许自行构造。"
    if old_34 in content:
        content = content.replace(old_34, new_34)
        print("✅ DEC2: 已修改 case_34 的 TextToSearchLogQuery criterion")
    else:
        print("⚠️ DEC2: 未找到 case_34 的目标文本")
    
    # DEC4: 修改 case_0 的归因分析 criterion
    old_0 = "洞察部分包含针对排名最高错误的归因分析：使用 count_if 量化特定特征（如 UserAgent、staffname、IP 段等）在错误集合中的出现比例与全量日志的比例对比，并以通俗语言表达关联强度（如'HeadlessChrome 的报错概率是普通请求的 35 倍'），而非仅列举建议或泛化描述"
    new_0 = "【加分项】洞察部分包含深度归因分析：使用 count_if 量化特定特征在错误集合 vs 全量日志中的比例对比。注：此条为增值服务要求，基础排序查询可不满足。"
    if old_0 in content:
        content = content.replace(old_0, new_0)
        print("✅ DEC4: 已修改 case_0 的归因分析 criterion")
    else:
        print("⚠️ DEC4: 未找到 case_0 的目标文本")
    
    # DEC5: 删除 case_38 的"不包含 GetTopicInfoByName"正向得分项
    # 使用正则表达式删除该 criterion 块
    pattern = r'- criterion: 工具调用序列中不包含 GetTopicInfoByName，直接将用户提供的 UUID（[^）]+）作为参数传入后续工具（如 SearchLog）。\n  points: 10\n  tags:\n  - axis:efficiency\n  - type:positive\n'
    matches = re.findall(pattern, content)
    if matches:
        content = re.sub(pattern, '', content)
        print(f"✅ DEC5: 已删除 case_38 的'不包含 GetTopicInfoByName'正向得分项 (找到 {len(matches)} 处)")
    else:
        print("⚠️ DEC5: 未找到 case_38 的目标文本")
    
    # DEC6: 修改 case_38 的 CASE WHEN criterion
    old_38 = "TextToSearchLogQuery 生成的查询语句中使用了 CASE WHEN 将不同状态码（至少覆盖 2xx、3xx、4xx、5xx 四类）各自转为独立的统计列（每列一个 SUM/COUNT CASE WHEN），而非用 COUNT(*) GROUP BY status 输出行统计结果。"
    new_38 = "实现了以域名为行、状态码为列的统计展示（通过 CASE WHEN 生成或行式聚合后手动整理均可）。注：若因 CLS 语法限制采用替代方案，需在输出中说明。"
    if old_38 in content:
        content = content.replace(old_38, new_38)
        print("✅ DEC6: 已修改 case_38 的 CASE WHEN criterion")
    else:
        print("⚠️ DEC6: 未找到 case_38 的目标文本")
    
    # 写回文件
    with open(yaml_path, 'w') as f:
        f.write(content)
    
    print("\ntestcases.yaml 修改完成！")
    
    # DEC3: 修改 prompt.md 增加对比分析执行指导
    prompt_path = '/Users/wenxinhuang/Documents/all_in_one/项目/meta-agent/source/cls-log-agent/prompt.md'
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # 在"复合需求拆分"部分增加对比分析指导
    old_section = "### 复合需求拆分\n当用户需求包含多个独立分析目标（如'对比今天和昨天的错误数'、'查看北京和上海的地域分布'）时，应拆成多次调用而非揉入一条 SQL。"
    new_section = """### 复合需求拆分
当用户需求包含多个独立分析目标（如'对比今天和昨天的错误数'、'查看北京和上海的地域分布'）时，应拆成多次调用而非揉入一条 SQL。

**对比分析场景特别指导**：
当用户要求对比两种不同计算方式（如 floor vs ceil、昨天 vs 今天、方案A vs 方案B）时：
- **必须分别执行独立查询**，禁止将对比维度合并到同一个 GROUP BY 中
- 错误示例：`GROUP BY response_time_floor, response_time_ceil`（会导致数据重复统计）
- 正确做法：先执行 `GROUP BY response_time_floor`，再执行 `GROUP BY response_time_ceil`，最后对比两套结果"""
    
    if old_section in prompt_content:
        prompt_content = prompt_content.replace(old_section, new_section)
        print("✅ DEC3: 已在 prompt.md 中增加对比分析执行指导")
    else:
        print("⚠️ DEC3: 未找到 prompt.md 中的目标文本")
    
    with open(prompt_path, 'w') as f:
        f.write(prompt_content)
    
    print("\nprompt.md 修改完成！")
    print("\n所有校准修复已应用。")

if __name__ == "__main__":
    main()
