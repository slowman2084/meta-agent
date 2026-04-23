#!/usr/bin/env python3
"""
YAML 测试用例工具 — 替代 yq CLI

提供对 testcases.yaml 的按需读写能力，避免一次性加载整个大文件到 LLM 上下文中。
用于替代项目中所有对 yq 外部命令的依赖。

子命令:
  count         获取测试用例总数
  get           读取特定索引的用例（支持字段过滤）
  set           修改特定用例的特定字段
  validate      验证 YAML 文件格式
  export-inputs 导出所有 Input 为批量 JSON（供 Platform Skill 使用）

用法:
  ./venv/bin/python scripts/yaml_tool.py count <yaml_path>
  ./venv/bin/python scripts/yaml_tool.py get <yaml_path> <index> [--fields Input,Judge]
  ./venv/bin/python scripts/yaml_tool.py set <yaml_path> <index> --field Judge --value-file judge.yaml
  ./venv/bin/python scripts/yaml_tool.py validate <yaml_path>

示例:
  # 获取用例总数
  ./venv/bin/python scripts/yaml_tool.py count source/cls-log-agent/testcases.yaml

  # 读取第 0 条用例
  ./venv/bin/python scripts/yaml_tool.py get source/cls-log-agent/testcases.yaml 0

  # 只读取第 0 条用例的 Input 和 Judge 字段
  ./venv/bin/python scripts/yaml_tool.py get source/cls-log-agent/testcases.yaml 0 --fields Input,Judge

  # 读取多条用例（逗号分隔或范围）
  ./venv/bin/python scripts/yaml_tool.py get source/cls-log-agent/testcases.yaml 0,1,2
  ./venv/bin/python scripts/yaml_tool.py get source/cls-log-agent/testcases.yaml 0-4

  # 修改第 3 条用例的 Judge 字段（从文件读取值）
  ./venv/bin/python scripts/yaml_tool.py set source/cls-log-agent/testcases.yaml 3 --field Judge --value-file judge.yaml

  # 修改第 3 条用例的 ExpectedOutput 字段（从 stdin 读取值）
  echo "expected output text" | ./venv/bin/python scripts/yaml_tool.py set source/cls-log-agent/testcases.yaml 3 --field ExpectedOutput --value-stdin

  # 验证 YAML 格式
  ./venv/bin/python scripts/yaml_tool.py validate source/cls-log-agent/testcases.yaml
"""

import sys
import os
import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 启用实时输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# 使用 ruamel.yaml 保留 YAML 格式（注释、顺序、多行字符串样式等）
# 回退到 pyyaml（项目 requirements.txt 中两者都有）
try:
    from ruamel.yaml import YAML as RuamelYAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False

import yaml  # pyyaml 作为兜底


# ============================================================
# 低层 YAML 读写（ruamel 优先，pyyaml 兜底）
# ============================================================

def _load_yaml(path: Path):
    """读取 YAML 文件，返回 Python 数据结构。
    读操作优先使用 pyyaml（性能更好），写操作仍用 ruamel（保留格式）。
    """
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _load_yaml_for_write(path: Path):
    """读取 YAML 文件（用于后续写回），优先 ruamel 以保留格式。"""
    if HAS_RUAMEL:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                ry = RuamelYAML()
                ry.preserve_quotes = True
                return ry.load(f)
        except Exception:
            print("⚠️  ruamel.yaml 解析失败，回退到 pyyaml", file=sys.stderr, flush=True)
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)


def _dump_yaml(data, path: Path):
    """写回 YAML 文件，尽量保留格式"""
    with open(path, 'w', encoding='utf-8') as f:
        if HAS_RUAMEL:
            ry = RuamelYAML()
            ry.preserve_quotes = True
            ry.default_flow_style = False
            ry.allow_unicode = True
            ry.width = 4096  # 避免过度换行
            ry.dump(data, f)
        else:
            yaml.dump(
                data, f,
                allow_unicode=True,
                default_flow_style=False,
                indent=2,
                sort_keys=False
            )


def _dump_yaml_to_str(data) -> str:
    """将 Python 数据结构序列化为 YAML 字符串"""
    if HAS_RUAMEL:
        from io import StringIO
        ry = RuamelYAML()
        ry.preserve_quotes = True
        ry.default_flow_style = False
        ry.allow_unicode = True
        ry.width = 4096
        buf = StringIO()
        ry.dump(data, buf)
        return buf.getvalue()
    else:
        return yaml.dump(
            data,
            allow_unicode=True,
            default_flow_style=False,
            indent=2,
            sort_keys=False
        )


# ============================================================
# 格式兼容层
# ============================================================

def _get_cases(data) -> list:
    """兼容两种根键格式：
    - meta-agent 标准格式：{cases: [...]}
    - pptdog 外部格式：{testcases: [...]}
    返回用例列表，未找到时返回空列表。
    """
    if not isinstance(data, dict):
        return []
    if 'cases' in data:
        return data.get('cases', [])
    if 'testcases' in data:
        # pptdog 格式：字段名映射到标准字段名
        raw = data.get('testcases', [])
        converted = []
        for tc in raw:
            if not isinstance(tc, dict):
                converted.append(tc)
                continue
            c = dict(tc)
            # input -> Input, expected_output -> ExpectedOutput, judge -> Judge
            if 'input' in c and 'Input' not in c:
                c['Input'] = c.pop('input')
            if 'expected_output' in c and 'ExpectedOutput' not in c:
                c['ExpectedOutput'] = c.pop('expected_output')
            if 'judge' in c and 'Judge' not in c:
                judge_val = c.pop('judge')
                if isinstance(judge_val, list):
                    c['Judge'] = '\n'.join(judge_val)
                else:
                    c['Judge'] = judge_val
            converted.append(c)
        return converted
    return []


# ============================================================
# 索引解析
# ============================================================

def parse_indices(spec: str, total: int) -> List[int]:
    """
    解析索引规格字符串，支持:
    - 单索引: "3"
    - 逗号分隔: "0,1,2"
    - 范围: "0-4" (含首含尾)
    - 混合: "0,2-4,7"
    """
    indices = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start = int(start_s.strip())
            end = int(end_s.strip())
            for i in range(start, end + 1):
                if 0 <= i < total:
                    indices.append(i)
                else:
                    print(f"⚠️  索引 {i} 超出范围 (0-{total - 1})，跳过", file=sys.stderr, flush=True)
        else:
            i = int(part)
            if 0 <= i < total:
                indices.append(i)
            else:
                print(f"⚠️  索引 {i} 超出范围 (0-{total - 1})，跳过", file=sys.stderr, flush=True)
    # 去重保序
    seen = set()
    result = []
    for i in indices:
        if i not in seen:
            seen.add(i)
            result.append(i)
    return result


# ============================================================
# 子命令实现
# ============================================================

def cmd_count(args):
    """获取测试用例总数"""
    path = Path(args.yaml_path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr, flush=True)
        return 1

    data = _load_yaml(path)
    cases = _get_cases(data)
    count = len(cases)

    if args.json:
        print(json.dumps({"count": count}), flush=True)
    else:
        print(count, flush=True)
    return 0


def cmd_get(args):
    """读取特定索引的用例"""
    path = Path(args.yaml_path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr, flush=True)
        return 1

    data = _load_yaml(path)
    cases = _get_cases(data)
    total = len(cases)

    if total == 0:
        print("⚠️  用例列表为空", file=sys.stderr, flush=True)
        return 1

    indices = parse_indices(args.index, total)
    if not indices:
        print("❌ 未解析到任何有效索引", file=sys.stderr, flush=True)
        return 1

    # 字段过滤
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(',')]

    results = []
    for idx in indices:
        case = cases[idx]
        if fields:
            # 只保留指定字段
            if HAS_RUAMEL:
                from ruamel.yaml.comments import CommentedMap
                filtered = CommentedMap()
            else:
                filtered = {}
            for f in fields:
                if f in case:
                    filtered[f] = case[f]
                else:
                    print(f"⚠️  case[{idx}] 不含字段 '{f}'", file=sys.stderr, flush=True)
            results.append(filtered)
        else:
            results.append(case)

    # 输出
    if len(results) == 1:
        output = _dump_yaml_to_str(results[0])
    else:
        output = _dump_yaml_to_str(results)

    print(output, end='', flush=True)
    return 0


def cmd_set(args):
    """修改特定用例的特定字段"""
    path = Path(args.yaml_path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr, flush=True)
        return 1

    # 读取新值
    if args.value_file:
        value_path = Path(args.value_file)
        if not value_path.exists():
            print(f"❌ 值文件不存在: {value_path}", file=sys.stderr, flush=True)
            return 1
        with open(value_path, 'r', encoding='utf-8') as f:
            raw = f.read()
    elif args.value_stdin:
        raw = sys.stdin.read()
    elif args.value is not None:
        raw = args.value
    else:
        print("❌ 必须提供 --value-file、--value-stdin 或 --value 之一", file=sys.stderr, flush=True)
        return 1

    # 尝试将值解析为 YAML（以支持复杂结构如 Judge 列表）
    try:
        if HAS_RUAMEL:
            from io import StringIO
            ry = RuamelYAML()
            ry.preserve_quotes = True
            new_value = ry.load(StringIO(raw))
        else:
            new_value = yaml.safe_load(raw)
    except Exception:
        # 解析失败则作为纯字符串
        new_value = raw

    # 如果解析结果是 None 且原始内容非空，保留原字符串
    if new_value is None and raw.strip():
        new_value = raw.strip()

    # 加载 YAML（用于写回，保留格式）
    data = _load_yaml_for_write(path)
    cases = _get_cases(data)
    total = len(cases)

    idx = int(args.index)
    if idx < 0 or idx >= total:
        print(f"❌ 索引 {idx} 超出范围 (0-{total - 1})", file=sys.stderr, flush=True)
        return 1

    # 备份（如指定）
    if args.backup:
        bak_dir = path.parent / "bak"
        bak_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak_path = bak_dir / f"testcases_{ts}.yaml.bak"
        shutil.copy2(path, bak_path)
        print(f"📦 已备份到: {bak_path}", file=sys.stderr, flush=True)

    # 修改
    field = args.field
    old_value = cases[idx].get(field, '<未设置>')
    cases[idx][field] = new_value

    # 写回
    _dump_yaml(data, path)

    print(f"✅ 已更新 case[{idx}].{field}", file=sys.stderr, flush=True)
    return 0


def cmd_validate(args):
    """验证 YAML 文件格式"""
    path = Path(args.yaml_path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr, flush=True)
        return 1

    errors = []
    warnings = []

    # 1. 能否正确解析
    try:
        data = _load_yaml(path)
    except Exception as e:
        print(f"❌ YAML 解析失败: {e}", flush=True)
        return 1

    if data is None:
        print("❌ YAML 文件内容为空", flush=True)
        return 1

    # 2. 顶层结构
    if not isinstance(data, dict):
        errors.append(f"顶层应为字典，实际为 {type(data).__name__}")
    else:
        if 'cases' not in data and 'testcases' not in data:
            errors.append("缺少 'cases' 或 'testcases' 键")
        else:
            cases = _get_cases(data)
            if not isinstance(cases, list):
                errors.append(f"用例列表应为列表，实际为 {type(cases).__name__}")
                cases = []
            total = len(cases)

            if 'meta' in data and isinstance(data['meta'], dict):
                declared_count = data['meta'].get('count')
                if declared_count is not None and declared_count != total:
                    warnings.append(f"meta.count={declared_count} 与实际用例数 {total} 不一致")

            # 3. 逐条检查
            for i, case in enumerate(cases):
                if not isinstance(case, dict):
                    errors.append(f"cases[{i}] 应为字典，实际为 {type(case).__name__}")
                    continue

                # 必须有 Input
                if 'Input' not in case:
                    errors.append(f"cases[{i}] 缺少 'Input' 字段")
                elif not case['Input'] or (isinstance(case['Input'], str) and not case['Input'].strip()):
                    warnings.append(f"cases[{i}].Input 为空")

                # ExpectedOutput 和 Judge 可选但建议存在
                if 'ExpectedOutput' not in case:
                    warnings.append(f"cases[{i}] 缺少 'ExpectedOutput' 字段")

                if 'Judge' not in case:
                    warnings.append(f"cases[{i}] 缺少 'Judge' 字段")
                elif case['Judge']:
                    # 如果 Judge 是列表，检查 rubric 结构
                    judge = case['Judge']
                    if isinstance(judge, list):
                        for j, rubric in enumerate(judge):
                            if isinstance(rubric, dict):
                                for req_field in ['criterion', 'points']:
                                    if req_field not in rubric:
                                        warnings.append(f"cases[{i}].Judge[{j}] 缺少 '{req_field}' 字段")

    # 输出
    file_size_kb = os.path.getsize(path) / 1024
    total_cases = len(_get_cases(data)) if isinstance(data, dict) else 0

    if args.json:
        result = {
            "valid": len(errors) == 0,
            "file": str(path),
            "size_kb": round(file_size_kb, 2),
            "cases_count": total_cases,
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    else:
        print(f"📄 文件: {path}", flush=True)
        print(f"📏 大小: {file_size_kb:.2f} KB", flush=True)
        print(f"📊 用例数: {total_cases}", flush=True)
        print(flush=True)

        if errors:
            print(f"❌ 发现 {len(errors)} 个错误:", flush=True)
            for e in errors:
                print(f"   • {e}", flush=True)
        else:
            print("✅ 格式验证通过", flush=True)

        if warnings:
            print(f"\n⚠️  {len(warnings)} 个警告:", flush=True)
            for w in warnings:
                print(f"   • {w}", flush=True)

    return 1 if errors else 0


# ============================================================
# export-inputs 子命令
# ============================================================

def cmd_export_inputs(args):
    """导出所有/指定范围的 Input 为批量 JSON，供 Platform Skill 批量执行使用。"""
    path = Path(args.yaml_path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", flush=True)
        return 1

    data = _load_yaml(path)
    if not isinstance(data, dict) or ('cases' not in data and 'testcases' not in data):
        print("❌ YAML 格式错误: 缺少 'cases' 或 'testcases' 字段", flush=True)
        return 1

    cases = _get_cases(data)
    total = len(cases)

    # 解析索引范围
    if args.cases:
        indices = _parse_indices(args.cases, total)
    else:
        indices = list(range(total))

    # 构建输出
    entries = []
    for idx in indices:
        if 0 <= idx < total:
            case = cases[idx]
            input_text = case.get('Input', '')
            if isinstance(input_text, str):
                input_text = input_text.strip()
            entries.append({"index": idx, "input": input_text or ""})

    output_json = json.dumps(entries, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"✅ 已导出 {len(entries)} 条 Input 到: {out_path}", flush=True)
    else:
        print(output_json, flush=True)

    return 0


def _parse_indices(spec: str, total: int) -> List[int]:
    """解析索引规范: '0', '0-4', '0,2,5', '0-4,7,9-11'"""
    indices = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            start = int(start.strip())
            end = int(end.strip())
            indices.extend(range(start, min(end + 1, total)))
        else:
            indices.append(int(part))
    return sorted(set(indices))


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog='yaml_tool',
        description='YAML 测试用例工具 — 替代 yq CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 获取用例总数
  %(prog)s count source/agent/testcases.yaml

  # 读取第 0 条用例（仅 Input 和 Judge）
  %(prog)s get source/agent/testcases.yaml 0 --fields Input,Judge

  # 读取第 0-4 条用例
  %(prog)s get source/agent/testcases.yaml 0-4

  # 修改第 3 条用例的 Judge（从文件读取）
  %(prog)s set source/agent/testcases.yaml 3 --field Judge --value-file judge.yaml

  # 验证 YAML 格式
  %(prog)s validate source/agent/testcases.yaml
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')
    subparsers.required = True

    # --- count ---
    p_count = subparsers.add_parser('count', help='获取测试用例总数')
    p_count.add_argument('yaml_path', help='YAML 文件路径')
    p_count.add_argument('--json', action='store_true', help='以 JSON 格式输出')
    p_count.set_defaults(func=cmd_count)

    # --- get ---
    p_get = subparsers.add_parser('get', help='读取特定索引的用例')
    p_get.add_argument('yaml_path', help='YAML 文件路径')
    p_get.add_argument('index', help='用例索引（如 0, 0-4, 0,2,5）')
    p_get.add_argument('--fields', '-f', help='只输出指定字段（逗号分隔，如 Input,Judge）')
    p_get.set_defaults(func=cmd_get)

    # --- set ---
    p_set = subparsers.add_parser('set', help='修改特定用例的特定字段')
    p_set.add_argument('yaml_path', help='YAML 文件路径')
    p_set.add_argument('index', help='用例索引')
    p_set.add_argument('--field', required=True, help='要修改的字段名')
    p_set.add_argument('--value-file', help='从文件读取新值')
    p_set.add_argument('--value-stdin', action='store_true', help='从 stdin 读取新值')
    p_set.add_argument('--value', help='直接指定新值（简单字符串）')
    p_set.add_argument('--backup', '-b', action='store_true', default=True, help='修改前备份（默认开启）')
    p_set.add_argument('--no-backup', action='store_false', dest='backup', help='不备份')
    p_set.set_defaults(func=cmd_set)

    # --- validate ---
    p_validate = subparsers.add_parser('validate', help='验证 YAML 文件格式')
    p_validate.add_argument('yaml_path', help='YAML 文件路径')
    p_validate.add_argument('--json', action='store_true', help='以 JSON 格式输出')
    p_validate.set_defaults(func=cmd_validate)

    # --- export-inputs ---
    p_export = subparsers.add_parser('export-inputs', help='导出 Input 为批量 JSON（供 Platform Skill 使用）')
    p_export.add_argument('yaml_path', help='YAML 文件路径')
    p_export.add_argument('--cases', help='用例索引范围（如 0-4, 0,2,5）。不指定则导出全部')
    p_export.add_argument('--output', '-o', help='输出 JSON 文件路径（不指定则输出到 stdout）')
    p_export.set_defaults(func=cmd_export_inputs)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
