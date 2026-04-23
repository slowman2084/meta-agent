#!/usr/bin/env python3
"""
Sample Platform 执行脚本 — 演示如何实现平台适配

用法:
    ./venv/bin/python source/platform-skills/sample_platform/scripts/execute.py \\
        --inputs inputs.json \\
        --prompt prompt.md \\
        --output-dir ./output/ \\
        --config config/platform.yaml

这是一个脱敏的 Sample 脚本，展示 Platform Skill 执行脚本的基本结构。
实际使用时请替换 call_platform_api() 中的 API 调用逻辑。
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# =====================================================
# 配置
# =====================================================
DEFAULT_CONFIG = {
    "API_ENDPOINT": "https://api.example.com/v1",
    "API_KEY": "",
    "MODEL": "gpt-4o",
    "TIMEOUT": 120,
    "MAX_CONCURRENT": 3,
    "MAX_RETRIES": 3,
    "RETRY_DELAY": 2,
}


def load_config(config_path):
    """加载平台配置"""
    if not config_path or not os.path.exists(config_path):
        print("⚠️ 未找到配置文件，使用默认配置", flush=True)
        return DEFAULT_CONFIG

    # 实际实现中使用 yaml.safe_load
    print(f"   加载配置: {config_path}", flush=True)
    return DEFAULT_CONFIG


def call_platform_api(prompt, user_input, config):
    """
    调用平台 API 执行单条用例

    返回:
        {
            "result": "最终文本输出",
            "conversations": [ShareGPT 格式对话记录]
        }

    TODO: 替换为实际的 API 调用逻辑
    """
    # ============================================
    # 🔧 在此替换为你的平台 API 调用
    # ============================================
    raise NotImplementedError(
        "这是一个 Sample 脚本。请替换 call_platform_api() 中的逻辑。\n"
        "参考 SKILL.md 中的 ShareGPT 格式规范。"
    )


def execute_case(case_idx, user_input, prompt, config, output_dir):
    """执行单条用例"""
    max_retries = config.get("MAX_RETRIES", 3)
    retry_delay = config.get("RETRY_DELAY", 2)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"   尝试 {attempt}/{max_retries}...", end=" ", flush=True)
            response = call_platform_api(prompt, user_input, config)
            print("✅", flush=True)

            # 写入 actual_result
            result_path = os.path.join(output_dir, f"case_{case_idx}_actual_result.txt")
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(response["result"])

            # 写入 sharegpt.json
            sharegpt_path = os.path.join(output_dir, f"case_{case_idx}_sharegpt.json")
            sharegpt_data = {
                "conversations": response.get("conversations", []),
                "metadata": {
                    "agent_name": "",
                    "platform": config.get("name", "sample-platform"),
                    "model": config.get("MODEL", ""),
                    "timestamp": datetime.now().isoformat(),
                }
            }
            with open(sharegpt_path, "w", encoding="utf-8") as f:
                json.dump(sharegpt_data, f, ensure_ascii=False, indent=2)

            return True

        except NotImplementedError:
            raise
        except Exception as e:
            print(f"❌ {str(e)[:50]}", flush=True)
            if attempt < max_retries:
                print(f"   等待 {retry_delay * attempt} 秒后重试...", flush=True)
                time.sleep(retry_delay * attempt)
            else:
                # 写入错误信息
                result_path = os.path.join(output_dir, f"case_{case_idx}_actual_result.txt")
                with open(result_path, "w", encoding="utf-8") as f:
                    f.write(f"❌ 执行失败（{max_retries} 次重试后）: {e}")
                return False


def main():
    parser = argparse.ArgumentParser(
        description='Sample Platform 执行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  ./venv/bin/python scripts/execute.py --inputs inputs.json --prompt prompt.md --output-dir ./output/
        '''
    )
    parser.add_argument('--inputs', required=True, help='inputs.json 路径')
    parser.add_argument('--prompt', required=True, help='prompt.md / SKILL.md 路径')
    parser.add_argument('--output-dir', required=True, help='输出目录')
    parser.add_argument('--config', default=None, help='平台配置文件路径')
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("Sample Platform — 批量执行", flush=True)
    print("=" * 60, flush=True)

    # 1. 加载配置
    print("\n1️⃣ 加载配置...", flush=True)
    config = load_config(args.config)

    # 2. 读取 prompt
    print("\n2️⃣ 读取 prompt...", flush=True)
    with open(args.prompt, "r", encoding="utf-8") as f:
        prompt = f.read()
    print(f"   ✅ {len(prompt)} 字符", flush=True)

    # 3. 读取 inputs
    print("\n3️⃣ 读取 inputs...", flush=True)
    with open(args.inputs, "r", encoding="utf-8") as f:
        inputs = json.load(f)
    print(f"   ✅ {len(inputs)} 条用例", flush=True)

    # 4. 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 5. 批量执行
    print(f"\n4️⃣ 开始执行 ({len(inputs)} 条)...", flush=True)
    success = 0
    failed = 0
    failed_cases = []
    start_time = time.time()

    for i, item in enumerate(inputs):
        user_input = item.get("Input", item.get("input", str(item)))
        print(f"\n   [{i+1}/{len(inputs)}] case_{i}:", flush=True)
        try:
            ok = execute_case(i, user_input, prompt, config, args.output_dir)
            if ok:
                success += 1
            else:
                failed += 1
                failed_cases.append(f"case_{i}")
        except NotImplementedError as e:
            print(f"\n❌ {e}", flush=True)
            sys.exit(1)

    elapsed = time.time() - start_time

    # 6. 写入执行摘要
    summary = {
        "total": len(inputs),
        "success": success,
        "failed": failed,
        "failed_cases": failed_cases,
        "total_time_seconds": round(elapsed, 1),
        "avg_time_per_case_seconds": round(elapsed / max(len(inputs), 1), 1),
        "platform": config.get("name", "sample-platform"),
        "model": config.get("MODEL", ""),
    }
    summary_path = os.path.join(args.output_dir, "execution_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n" + "=" * 60, flush=True)
    print(f"✅ 执行完成: {success} 成功 / {failed} 失败 / {elapsed:.1f}s", flush=True)
    print(f"   摘要: {summary_path}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
