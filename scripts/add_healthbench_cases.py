#!/usr/bin/env python3
"""
自动从 HealthBench JSONL 导入测试用例并翻译为中文
"""

import json
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv
import openai

# 加载环境变量
load_dotenv()

# 配置 OpenAI
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
# DSPY_MODEL 格式如 openai/gpt-4，这里提取 gpt-4
dspy_model = os.getenv("DSPY_MODEL", "openai/gpt-4")
if "/" in dspy_model:
    model = dspy_model.split("/", 1)[1]
else:
    model = dspy_model

if not api_key:
    print("❌ 未找到 OPENAI_API_KEY，请检查 .env 配置")
    sys.exit(1)

client = openai.OpenAI(api_key=api_key, base_url=base_url)

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
JSONL_PATH = PROJECT_ROOT / "source/meta-rubric-gen/references/healthbench_main.jsonl"
YAML_PATH = PROJECT_ROOT / "source/meta-rubric-gen/testcases.yaml"
COUNT = 20
START_INDEX = 5  # 跳过前5个（假设已存在）

def translate_batch(text_list):
    """批量翻译文本列表"""
    if not text_list:
        return []
    
    prompt = "请将以下 JSON 数组中的英文文本翻译成中文。保持 JSON 结构不变，只翻译值。不要添加额外解释。\n\n" + json.dumps(text_list, ensure_ascii=False)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的医疗翻译助手。请直接返回翻译后的 JSON 数组，不要包含 Markdown 格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        # 清理 Markdown 代码块标记
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        return json.loads(content)
    except Exception as e:
        print(f"⚠️ 翻译失败: {e}")
        return text_list

def translate_single(text):
    """翻译单个文本"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的医疗翻译助手。请将以下文本翻译成流畅、专业的中文。"},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ 翻译失败: {e}")
        return text

def process_rubrics(rubrics):
    """处理 Rubrics 列表，批量翻译 criterion"""
    criteria = [item["criterion"] for item in rubrics if "criterion" in item]
    
    if not criteria:
        return rubrics
        
    print(f"   正在翻译 {len(criteria)} 条评分标准...")
    translated_criteria = translate_batch(criteria)
    
    if len(translated_criteria) != len(criteria):
        print(f"⚠️ 翻译数量不匹配 ({len(translated_criteria)} vs {len(criteria)})，使用原文")
        return rubrics
        
    new_rubrics = []
    idx = 0
    for item in rubrics:
        new_item = item.copy()
        if "criterion" in new_item:
            new_item["criterion"] = translated_criteria[idx]
            idx += 1
        new_rubrics.append(new_item)
    return new_rubrics

def main():
    if not JSONL_PATH.exists():
        print(f"❌ 文件不存在: {JSONL_PATH}")
        sys.exit(1)

    print(f"🚀 开始处理 HealthBench 数据")
    print(f"   源文件: {JSONL_PATH}")
    print(f"   目标文件: {YAML_PATH}")
    print(f"   模型: {model}")
    print(f"   计划添加: {COUNT} 条 (从第 {START_INDEX+1} 条开始)")

    new_cases = []
    
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        # 读取所有行，取指定范围
        lines = f.readlines()
        target_lines = lines[START_INDEX : START_INDEX + COUNT]

    for i, line in enumerate(target_lines):
        try:
            data = json.loads(line)
            current_idx = START_INDEX + i + 1
            
            # 1. 提取并翻译 Input
            original_input = data["prompt"][0]["content"]
            print(f"[{i+1}/{COUNT}] (ID: {current_idx}) 正在翻译 Input...")
            translated_input = translate_single(original_input)
            
            input_text = f"Task: 请为以下用户请求生成评分标准 (Rubrics)。\n\n[用户]: {translated_input}\n\nRequirements: 生成一组原子化的评分条目。每个条目应包含分值 (points) 和清晰的描述。"

            # 2. 提取并翻译 Rubrics
            original_rubrics = data["rubrics"]
            translated_rubrics = process_rubrics(original_rubrics)
            
            # 3. 格式化 ExpectedOutput 为 JSON 字符串 (Pretty Print)
            expected_output_json = json.dumps(translated_rubrics, ensure_ascii=False, indent=2)

            # 4. 构建 Case
            case = {
                "Input": input_text,
                "ExpectedOutput": expected_output_json
            }
            new_cases.append(case)
            
        except json.JSONDecodeError:
            print(f"⚠️ 跳过无效 JSON 行: {current_idx}")
            continue
        except Exception as e:
            print(f"⚠️ 处理行 {current_idx} 失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 追加到 YAML
    if new_cases:
        print(f"💾 正在追加 {len(new_cases)} 条用例到 {YAML_PATH}...")
        
        with open(YAML_PATH, "a", encoding="utf-8") as f:
            for case in new_cases:
                # 使用 |+ 块标量保持换行
                f.write("- Input: |\n")
                # 缩进 Input 内容
                for line in case["Input"].split("\n"):
                    f.write(f"    {line}\n")
                
                f.write("  ExpectedOutput: |\n")
                # 缩进 ExpectedOutput 内容
                for line in case["ExpectedOutput"].split("\n"):
                    f.write(f"    {line}\n")
        
        # 更新 meta count
        try:
            with open(YAML_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 简单的正则替换更新 count
            import re
            old_count_match = re.search(r"count:\s*(\d+)", content)
            if old_count_match:
                old_count = int(old_count_match.group(1))
                new_count = old_count + len(new_cases)
                new_content = re.sub(r"count:\s*\d+", f"count: {new_count}", content, count=1)
                
                with open(YAML_PATH, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"✅ 更新用例总数为: {new_count}")
        except Exception as e:
            print(f"⚠️ 更新 meta count 失败: {e}")

        print("✅ 全部完成！")
    else:
        print("⚠️ 未生成任何新用例")

if __name__ == "__main__":
    main()
