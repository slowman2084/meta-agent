#!/usr/bin/env python3
"""
平台输出校验脚本

用途：
- 校验某个测试输出目录中的产物是否全部来自同一个平台
- 防止 `@tcop` / `@claude` / `@codebuddycli` / `@subagent` 结果混写到同一目录
- 在评估前快速发现目录污染、缺失文件、元数据不一致等问题

示例：
  ./venv/bin/python scripts/validate_platform_outputs.py \
    source/cls-log-agent/tmp/evalooper_iter_2_tcop \
    --expected-platform tcop \
    --expected-cases 1,4,8,14,15,17,28,30

  ./venv/bin/python scripts/validate_platform_outputs.py \
    source/cls-log-agent/tmp/test_20260321_tcop
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

DEFAULT_CONFIG = {
    "DEFAULT_PLATFORM": None,
}

CASE_FILE_RE = re.compile(r"^case_(\d+)_sharegpt\.json$")


def parse_case_spec(spec: str | None) -> list[int]:
    """解析 `1,2,5-7` 形式的 case 选择字符串。"""
    if not spec:
        return []

    result: set[int] = set()
    for part in spec.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_str, end_str = item.split("-", 1)
            start = int(start_str.strip())
            end = int(end_str.strip())
            if end < start:
                raise ValueError(f"无效范围: {item}")
            result.update(range(start, end + 1))
        else:
            result.add(int(item))
    return sorted(result)


def infer_platform_from_dir(output_dir: Path) -> str | None:
    """从目录名后缀推断平台，例如 `evalooper_iter_2_tcop` -> `tcop`。"""
    name = output_dir.name.strip()
    if not name or "_" not in name:
        return None
    suffix = name.rsplit("_", 1)[-1].strip()
    return suffix or None


def load_json_file(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_case_indices(output_dir: Path) -> list[int]:
    indices = []
    for file_path in sorted(output_dir.iterdir()):
        match = CASE_FILE_RE.match(file_path.name)
        if match:
            indices.append(int(match.group(1)))
    return sorted(indices)


def validate_sharegpt_file(file_path: Path, expected_platform: str) -> list[str]:
    errors: list[str] = []

    try:
        data = load_json_file(file_path)
    except FileNotFoundError:
        return [f"缺少文件: {file_path.name}"]
    except json.JSONDecodeError as e:
        return [f"JSON 解析失败: {file_path.name} ({e})"]
    except Exception as e:
        return [f"读取失败: {file_path.name} ({e})"]

    if not isinstance(data, dict):
        return [f"格式错误: {file_path.name} 顶层不是对象"]

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return [f"格式错误: {file_path.name} 缺少 metadata 对象"]

    actual_platform = str(metadata.get("platform", "")).strip()
    if actual_platform != expected_platform:
        errors.append(
            f"平台不匹配: {file_path.name} metadata.platform={actual_platform!r}，期望 {expected_platform!r}"
        )

    case_match = CASE_FILE_RE.match(file_path.name)
    expected_case_index = int(case_match.group(1)) if case_match else None
    actual_case_index = metadata.get("case_index")
    if expected_case_index is not None and actual_case_index != expected_case_index:
        errors.append(
            f"case_index 不匹配: {file_path.name} metadata.case_index={actual_case_index!r}，文件名为 case_{expected_case_index}"
        )

    return errors


def validate_batch_summary(output_dir: Path, expected_platform: str) -> list[str]:
    errors: list[str] = []
    summary_path = output_dir / "batch_summary.json"
    if not summary_path.exists():
        return errors

    try:
        data = load_json_file(summary_path)
    except json.JSONDecodeError as e:
        return [f"JSON 解析失败: batch_summary.json ({e})"]
    except Exception as e:
        return [f"读取失败: batch_summary.json ({e})"]

    if not isinstance(data, dict):
        return ["格式错误: batch_summary.json 顶层不是对象"]

    actual_platform = str(data.get("platform", "")).strip()
    if actual_platform != expected_platform:
        errors.append(
            f"batch_summary.json 平台不匹配: platform={actual_platform!r}，期望 {expected_platform!r}"
        )

    return errors


def build_report(output_dir: Path, expected_platform: str, expected_cases: list[int]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    found_cases = collect_case_indices(output_dir)
    cases_to_check = expected_cases or found_cases

    if not found_cases:
        errors.append("目录中没有找到任何 case_[N]_sharegpt.json 文件")

    missing_expected_cases = [idx for idx in expected_cases if idx not in found_cases]
    for idx in missing_expected_cases:
        errors.append(f"缺少期望用例: case_{idx}_sharegpt.json")

    for idx in cases_to_check:
        sharegpt_path = output_dir / f"case_{idx}_sharegpt.json"
        actual_path = output_dir / f"case_{idx}_actual_result.txt"

        if not sharegpt_path.exists():
            errors.append(f"缺少 ShareGPT 文件: {sharegpt_path.name}")
            continue
        if not actual_path.exists():
            errors.append(f"缺少实际输出文件: {actual_path.name}")

        errors.extend(validate_sharegpt_file(sharegpt_path, expected_platform))

    errors.extend(validate_batch_summary(output_dir, expected_platform))

    other_actual_files = []
    for file_path in sorted(output_dir.iterdir()):
        if file_path.name.startswith("case_") and file_path.name.endswith("_actual_result.txt"):
            idx_text = file_path.name[len("case_"):-len("_actual_result.txt")]
            if idx_text.isdigit() and int(idx_text) not in cases_to_check:
                other_actual_files.append(file_path.name)
    if other_actual_files and expected_cases:
        warnings.append(
            "目录中还存在未纳入本次校验的实际输出文件: " + ", ".join(other_actual_files[:10])
        )

    return {
        "output_dir": str(output_dir),
        "expected_platform": expected_platform,
        "expected_cases": expected_cases,
        "found_cases": found_cases,
        "checked_cases": cases_to_check,
        "errors": errors,
        "warnings": warnings,
        "ok": len(errors) == 0,
    }


def print_human_report(report: dict[str, Any]) -> None:
    print("=" * 70, flush=True)
    print("平台输出校验", flush=True)
    print("=" * 70, flush=True)
    print(f"目录: {report['output_dir']}", flush=True)
    print(f"期望平台: {report['expected_platform']}", flush=True)
    print(f"发现用例: {report['found_cases']}", flush=True)
    print(f"校验用例: {report['checked_cases']}", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)

    print("1️⃣ 步骤1: 校验平台一致性...", flush=True)
    if report["ok"]:
        print("   ✅ 未发现平台漂移或目录污染", flush=True)
    else:
        print(f"   ❌ 发现 {len(report['errors'])} 个问题", flush=True)
        for err in report["errors"]:
            print(f"   - {err}", flush=True)
    print(flush=True)

    print("2️⃣ 步骤2: 检查附加提示...", flush=True)
    if report["warnings"]:
        for warning in report["warnings"]:
            print(f"   ⚠️  {warning}", flush=True)
    else:
        print("   ✅ 无额外警告", flush=True)
    print(flush=True)

    print("3️⃣ 步骤3: 给出处理建议...", flush=True)
    if report["ok"]:
        print("   ✅ 可以继续做评估 / 汇总 / 迭代优化", flush=True)
    else:
        print("   ❌ 当前目录不应继续作为正式评估依据", flush=True)
        print("   建议:", flush=True)
        print("   - 将该目录标记为 mixed / diagnostic，仅用于诊断", flush=True)
        print("   - 在独立的正确平台目录中重跑缺失或污染的 case", flush=True)
        print("   - 禁止把 fallback 结果继续写回当前平台目录", flush=True)
    print(flush=True)

    print("=" * 70, flush=True)
    print("✅ 校验通过" if report["ok"] else "❌ 校验失败", flush=True)
    print("=" * 70, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="校验测试输出目录中的平台一致性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  ./venv/bin/python scripts/validate_platform_outputs.py \
    source/cls-log-agent/tmp/evalooper_iter_2_tcop \
    --expected-platform tcop \
    --expected-cases 1,4,8,14,15,17,28,30

  ./venv/bin/python scripts/validate_platform_outputs.py \
    source/cls-log-agent/tmp/test_20260321_tcop
        """,
    )
    parser.add_argument("output_dir", help="待校验的输出目录")
    parser.add_argument("--expected-platform", default=DEFAULT_CONFIG["DEFAULT_PLATFORM"],
                        help="期望平台名；若省略则尝试从目录名后缀推断")
    parser.add_argument("--expected-cases", default=None,
                        help="期望校验的 case 列表，如 1,2,5-7")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    if not output_dir.exists():
        print(f"❌ 输出目录不存在: {output_dir}", flush=True)
        return 2
    if not output_dir.is_dir():
        print(f"❌ 不是目录: {output_dir}", flush=True)
        return 2

    expected_platform = args.expected_platform or infer_platform_from_dir(output_dir)
    if not expected_platform:
        print("❌ 无法确定期望平台，请显式传入 --expected-platform", flush=True)
        return 2

    try:
        expected_cases = parse_case_spec(args.expected_cases)
    except ValueError as e:
        print(f"❌ --expected-cases 参数错误: {e}", flush=True)
        return 2

    report = build_report(output_dir, expected_platform, expected_cases)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    else:
        print_human_report(report)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
