#!/usr/bin/env python3
"""
平台批量测试脚本 — 对 @platform Agent 批量运行所有 CSV 测试用例

用法:
    ./venv/bin/python scripts/platform_test.py my-agent@platform
    ./venv/bin/python scripts/platform_test.py my-agent@platform --session my_test
    ./venv/bin/python scripts/platform_test.py my-agent@platform --timeout 600

流程:
1. 读取 source/[agent]@[platform]/platform.yaml + prompt.md → 生成 config_snapshot.yaml
2. 读取 source/[agent]@[platform]/testcases.csv
3. 逐条调用 react_agent_runner.py → 保存 execution_log.txt + actual_output.txt
4. 输出测试摘要
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python")


def find_runner():
    """Find react_agent_runner.py in source/*/skills/ directories."""
    for d in sorted(os.listdir(SOURCE_DIR)):
        candidate = os.path.join(
            SOURCE_DIR, d, "skills", "platform_react_runner",
            "scripts", "react_agent_runner.py",
        )
        if os.path.exists(candidate):
            return candidate
    return None


def prepare_config(agent_dir, output_dir):
    """Read platform.yaml + prompt.md, replace {{PROMPT}} placeholder, write config_snapshot."""
    yaml_path = os.path.join(agent_dir, "platform.yaml")
    prompt_path = os.path.join(agent_dir, "prompt.md")

    if not os.path.exists(yaml_path):
        print(f"❌ 找不到平台配置：{yaml_path}")
        sys.exit(1)
    if not os.path.exists(prompt_path):
        print(f"❌ 找不到提示词：{prompt_path}")
        sys.exit(1)

    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_content = f.read()
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_content = f.read()

    placeholder = "{{PROMPT}}"
    if placeholder not in yaml_content:
        print(f"⚠️  platform.yaml 中未找到 {placeholder} 占位符")
        sys.exit(1)

    lines = yaml_content.split("\n")
    result_lines = []
    for line in lines:
        if placeholder in line:
            indent = line[: len(line) - len(line.lstrip())]
            for pl in prompt_content.split("\n"):
                result_lines.append((indent + pl) if pl.strip() else indent)
        else:
            result_lines.append(line)

    result = "\n".join(result_lines)
    if placeholder in result:
        print(f"⚠️  替换后仍有残留 {placeholder}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    config_path = os.path.join(output_dir, "config_snapshot.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(result)

    return config_path


def read_csv_cases(csv_path):
    """Read test cases from CSV (Input, ExpectedOutput, Judge)."""
    if not os.path.exists(csv_path):
        print(f"❌ 找不到测试用例：{csv_path}")
        sys.exit(1)

    cases = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
    return cases


def extract_final_output(stdout):
    """Extract the last AI message from runner stdout (Node: agent blocks)."""
    blocks = re.split(r"={50,}\s*\n\s*Node:\s*(\w+)\s*\n\s*={50,}", stdout)
    last_agent_content = ""
    i = 1
    while i < len(blocks) - 1:
        node_name = blocks[i].strip()
        content = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
        if node_name == "agent":
            last_agent_content = content
        i += 2

    if last_agent_content:
        return last_agent_content

    lines = stdout.strip().split("\n")
    return "\n".join(lines[-20:]) if lines else "(no output)"


def run_single_case(runner_script, config_path, query, case_dir, timeout):
    """Run one test case, save logs and output."""
    os.makedirs(case_dir, exist_ok=True)

    query_path = os.path.join(case_dir, "query.txt")
    with open(query_path, "w", encoding="utf-8") as f:
        f.write(query)

    python_bin = VENV_PYTHON if os.path.exists(VENV_PYTHON) else "python3"
    cmd = [python_bin, runner_script, "--config", config_path, "--query", query]
    log_path = os.path.join(case_dir, "execution_log.txt")

    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=PROJECT_ROOT,
        )
        elapsed = time.time() - start
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(stdout)
            if stderr:
                f.write("\n\n=== STDERR ===\n")
                f.write(stderr)

        actual_output = extract_final_output(stdout)
        with open(os.path.join(case_dir, "actual_output.txt"), "w", encoding="utf-8") as f:
            f.write(actual_output)

        return {
            "success": result.returncode == 0,
            "actual_output": actual_output[:200],
            "elapsed": elapsed,
            "exit_code": result.returncode,
        }

    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        partial = (e.stdout or "") if hasattr(e, "stdout") else ""
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(partial)
            f.write(f"\n\n=== TIMEOUT after {timeout}s ===\n")

        return {
            "success": False,
            "actual_output": "(timeout)",
            "elapsed": elapsed,
            "exit_code": -1,
        }


def main():
    parser = argparse.ArgumentParser(description="平台批量测试")
    parser.add_argument("agent", help="Agent 名称 (如 my-agent@platform)")
    parser.add_argument("--session", default=None, help="Session ID (默认自动生成时间戳)")
    parser.add_argument("--timeout", type=int, default=300, help="单条用例超时秒数 (默认 300)")
    args = parser.parse_args()

    agent_name = args.agent
    agent_dir = os.path.join(SOURCE_DIR, agent_name)
    if not os.path.isdir(agent_dir):
        print(f"❌ 目录不存在：source/{agent_name}/")
        sys.exit(1)

    runner = find_runner()
    if runner is None:
        print("❌ 找不到 react_agent_runner.py")
        sys.exit(1)

    session = args.session or time.strftime("test_%Y%m%d_%H%M%S")
    output_dir = os.path.join(agent_dir, "tmp", session)

    print(f"🔧 平台批量测试：{agent_name}")
    print(f"   Runner：{runner}")
    print(f"   输出目录：source/{agent_name}/tmp/{session}/\n")

    config_path = prepare_config(agent_dir, output_dir)
    print(f"   ✅ 配置已准备：config_snapshot.yaml\n")

    csv_path = os.path.join(agent_dir, "testcases.csv")
    cases = read_csv_cases(csv_path)
    print(f"   📋 共 {len(cases)} 条用例\n")

    results = []
    for i, case in enumerate(cases, 1):
        query = case.get("Input", "").strip()
        if not query:
            print(f"   ⚠️  用例 {i}：Input 为空，跳过")
            continue

        print(f"   ▶ 用例 {i}/{len(cases)}：{query[:50]}...")
        case_dir = os.path.join(output_dir, f"case_{i}")
        r = run_single_case(runner, config_path, query, case_dir, args.timeout)
        results.append(r)

        status = "✅" if r["success"] else "❌"
        print(f"     {status} {r['elapsed']:.1f}s | {r['actual_output'][:80]}")
        print()

    ok = sum(1 for r in results if r["success"])
    print(f"{'='*50}")
    print(f"✅ 测试完成：{ok}/{len(results)} 成功")
    print(f"   输出目录：source/{agent_name}/tmp/{session}/")
    print(f"   每条用例的日志：case_N/execution_log.txt")
    print(f"   每条用例的输出：case_N/actual_output.txt")


if __name__ == "__main__":
    main()
