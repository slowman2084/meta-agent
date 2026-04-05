#!/usr/bin/env python3
"""
Skill 产物检查脚本

用途：检查 Skill 执行后生成的文件产物是否符合预期
     （文件存在性、大小、格式等基础验证）

用法:
    ./venv/bin/python scripts/artifact_checker.py <manifest_path>
    ./venv/bin/python scripts/artifact_checker.py <manifest_path> --base-dir /path/to/output
"""

import argparse
import json
import os
import sys

import yaml

# 启用实时输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


def read_manifest(path):
    """读取产物清单文件（YAML 或 JSON）"""
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".json"):
            return json.load(f)
        else:
            return yaml.safe_load(f)


def check_artifact(artifact_spec, base_dir):
    """检查单个产物

    artifact_spec 格式:
    {
        "path": "output/result.md",       # 相对路径（相对于 base_dir）
        "required": true,                  # 是否必须存在
        "min_size_bytes": 100,            # 最小文件大小（可选）
        "extension": ".md",               # 期望扩展名（可选）
        "contains": ["# Title"],          # 文件内容应包含的字符串（可选）
        "not_contains": ["ERROR"],        # 文件内容不应包含的字符串（可选）
    }
    """
    path = artifact_spec.get("path", "")
    required = artifact_spec.get("required", True)
    full_path = os.path.join(base_dir, path)

    result = {
        "path": path,
        "full_path": full_path,
        "checks": [],
        "passed": True,
    }

    # 检查 1：文件是否存在
    exists = os.path.exists(full_path)
    if not exists:
        if required:
            result["checks"].append({"check": "exists", "passed": False, "detail": "必需文件不存在"})
            result["passed"] = False
        else:
            result["checks"].append({"check": "exists", "passed": True, "detail": "可选文件不存在（跳过）"})
        return result

    result["checks"].append({"check": "exists", "passed": True, "detail": "文件存在"})

    # 检查 2：文件大小
    file_size = os.path.getsize(full_path)
    min_size = artifact_spec.get("min_size_bytes", 0)
    if file_size < min_size:
        result["checks"].append({
            "check": "min_size",
            "passed": False,
            "detail": f"文件大小 {file_size} 字节 < 最小要求 {min_size} 字节",
        })
        result["passed"] = False
    elif min_size > 0:
        result["checks"].append({
            "check": "min_size",
            "passed": True,
            "detail": f"文件大小 {file_size} 字节 >= {min_size} 字节",
        })

    # 检查 3：扩展名
    expected_ext = artifact_spec.get("extension")
    if expected_ext:
        actual_ext = os.path.splitext(full_path)[1]
        if actual_ext != expected_ext:
            result["checks"].append({
                "check": "extension",
                "passed": False,
                "detail": f"扩展名 '{actual_ext}' != 期望 '{expected_ext}'",
            })
            result["passed"] = False
        else:
            result["checks"].append({
                "check": "extension",
                "passed": True,
                "detail": f"扩展名匹配: {expected_ext}",
            })

    # 检查 4/5：内容包含/不包含
    contains = artifact_spec.get("contains", [])
    not_contains = artifact_spec.get("not_contains", [])

    if contains or not_contains:
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in contains:
                if pattern in content:
                    result["checks"].append({
                        "check": "contains",
                        "passed": True,
                        "detail": f"包含: '{pattern[:30]}'",
                    })
                else:
                    result["checks"].append({
                        "check": "contains",
                        "passed": False,
                        "detail": f"缺少: '{pattern[:30]}'",
                    })
                    result["passed"] = False

            for pattern in not_contains:
                if pattern not in content:
                    result["checks"].append({
                        "check": "not_contains",
                        "passed": True,
                        "detail": f"不含: '{pattern[:30]}'",
                    })
                else:
                    result["checks"].append({
                        "check": "not_contains",
                        "passed": False,
                        "detail": f"不应包含但找到: '{pattern[:30]}'",
                    })
                    result["passed"] = False

        except UnicodeDecodeError:
            result["checks"].append({
                "check": "content_read",
                "passed": True,
                "detail": "二进制文件，跳过内容检查",
            })

    return result


def run_artifact_check(manifest_path, base_dir=None):
    """执行产物检查"""
    print("=" * 70, flush=True)
    print("📦 Skill 产物检查", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)

    # ── 1. 读取清单 ──
    print("1️⃣  读取产物清单...", flush=True)

    manifest = read_manifest(manifest_path)
    if not manifest:
        print(f"  ❌ 无法读取清单: {manifest_path}", flush=True)
        return None

    artifacts = manifest.get("artifacts", manifest.get("expected_artifacts", []))
    if not artifacts:
        print(f"  ⚠️  清单中无产物定义", flush=True)
        return None

    if base_dir is None:
        base_dir = manifest.get("base_dir", os.path.dirname(manifest_path))

    print(f"  清单: {manifest_path}", flush=True)
    print(f"  基准目录: {base_dir}", flush=True)
    print(f"  产物数: {len(artifacts)}", flush=True)
    print(flush=True)

    # ── 2. 逐项检查 ──
    print("2️⃣  逐项检查...", flush=True)

    results = []
    passed_count = 0
    for i, spec in enumerate(artifacts):
        result = check_artifact(spec, base_dir)
        results.append(result)
        if result["passed"]:
            passed_count += 1

        emoji = "✅" if result["passed"] else "❌"
        print(f"  [{i+1}/{len(artifacts)}] {emoji} {result['path']}", flush=True)
        for check in result["checks"]:
            check_emoji = "  ✓" if check["passed"] else "  ✗"
            print(f"      {check_emoji} {check['detail']}", flush=True)
    print(flush=True)

    # ── 3. 汇总 ──
    all_passed = passed_count == len(artifacts)
    rate = passed_count / len(artifacts) if artifacts else 0

    print("=" * 70, flush=True)
    result_emoji = "✅" if all_passed else "❌"
    print(f"{result_emoji} 产物检查结果: {passed_count}/{len(artifacts)} 通过 ({rate:.0%})", flush=True)
    print("=" * 70, flush=True)

    return {
        "manifest_path": manifest_path,
        "base_dir": base_dir,
        "total": len(artifacts),
        "passed": passed_count,
        "failed": len(artifacts) - passed_count,
        "rate": rate,
        "all_passed": all_passed,
        "details": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="检查 Skill 执行后的文件产物",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
产物清单格式 (YAML):
  artifacts:
    - path: "output/result.md"
      required: true
      min_size_bytes: 100
      extension: ".md"
      contains: ["# Title"]
    - path: "output/log.json"
      required: false

示例用法:
  ./venv/bin/python scripts/artifact_checker.py manifest.yaml
  ./venv/bin/python scripts/artifact_checker.py manifest.yaml --base-dir /tmp/output
        """,
    )
    parser.add_argument("manifest", help="产物清单文件路径（YAML 或 JSON）")
    parser.add_argument("--base-dir", help="产物文件的基准目录（默认取清单中的 base_dir 或清单所在目录）")
    parser.add_argument("--output", "-o", help="将结果保存到 JSON 文件")

    args = parser.parse_args()

    result = run_artifact_check(args.manifest, base_dir=args.base_dir)

    if result is None:
        return 1

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 结果已保存: {args.output}", flush=True)

    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
