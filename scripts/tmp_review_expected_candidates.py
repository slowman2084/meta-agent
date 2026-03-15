#!/usr/bin/env python3
"""为指定 case 汇总当前 ExpectedOutput 与两个测试目录中的候选实际输出。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

try:
    from ruamel.yaml import YAML as RuamelYAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def load_yaml(path: Path):
    if HAS_RUAMEL:
        try:
            ry = RuamelYAML()
            ry.preserve_quotes = True
            with path.open('r', encoding='utf-8') as f:
                return ry.load(f)
        except Exception:
            pass
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='ignore').strip()


def summarize(text: str, max_len: int = 240) -> str:
    if not text:
        return ''
    lines = [re.sub(r'\s+', ' ', x).strip() for x in text.splitlines() if x.strip()]
    merged = ' | '.join(lines[:6])
    return merged[:max_len] + ('…' if len(merged) > max_len else '')


def features(text: str) -> dict:
    t = text or ''
    return {
        'chars': len(t),
        'lines': len([x for x in t.splitlines() if x.strip()]),
        'has_table': '|' in t and '---' in t,
        'has_sql': '```sql' in t.lower() or 'select ' in t.lower() or 'cql' in t.lower(),
        'has_time_range': bool(re.search(r'20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}', t)),
        'has_suggestion': any(k in t for k in ['建议', '下一步', '排查', '洞察']),
        'has_summary': any(k in t for k in ['摘要', '结论', '核心结论', '统计结果', '查询结果摘要']),
    }


def load_scores(result_dir: Path) -> dict[int, int]:
    scores: dict[int, int] = {}
    for p in result_dir.glob('case_*_eval_result.md'):
        m = re.match(r'case_(\d+)_eval_result\.md$', p.name)
        if not m:
            continue
        txt = read_text(p)
        sm = re.search(r'总分[：:]\s*(\d+)', txt)
        if sm:
            scores[int(m.group(1))] = int(sm.group(1))
    return scores


def classify_alignment(case_idx: int, yaml_input: str, dir_path: Path, candidate_name: str) -> str:
    """判断候选输出是否与当前 YAML 题目对齐。"""
    # 174731 默认认为与当前 YAML 对齐（该轮就是当前 40 case 的连续评估）
    if dir_path.name == 'test_20260315_174731':
        return 'aligned'

    input_file = dir_path / f'case_{case_idx}_input.txt'
    if not input_file.exists():
        if candidate_name.endswith('_actual_output.txt') and 'rerun' not in candidate_name:
            return 'probably_aligned'
        return 'unknown'

    candidate_input = read_text(input_file)
    if candidate_input == yaml_input:
        return 'aligned'
    return 'misaligned'


def main():
    parser = argparse.ArgumentParser(description='审阅指定 case 的候选输出')
    parser.add_argument('--yaml', required=True)
    parser.add_argument('--result-dir', action='append', required=True)
    parser.add_argument('--cases', required=True, help='逗号分隔 case 编号')
    parser.add_argument('--output-json', required=True)
    args = parser.parse_args()

    target_cases = [int(x.strip()) for x in args.cases.split(',') if x.strip()]
    yaml_data = load_yaml(Path(args.yaml))
    yaml_cases = yaml_data.get('cases', []) if isinstance(yaml_data, dict) else []

    result_dirs = [Path(x) for x in args.result_dir]
    score_maps = {d: load_scores(d) for d in result_dirs}

    report = []
    for idx in target_cases:
        item = {
            'case': idx,
            'input': str(yaml_cases[idx].get('Input', '') or '') if idx < len(yaml_cases) else '',
            'current_expected': {},
            'candidates': [],
        }
        if idx < len(yaml_cases):
            exp = str(yaml_cases[idx].get('ExpectedOutput', '') or '')
            item['current_expected'] = {
                'summary': summarize(exp),
                'features': features(exp),
            }

        for d in result_dirs:
            base = d / f'case_{idx}_actual_output.txt'
            if base.exists():
                text = read_text(base)
                item['candidates'].append({
                    'file': str(base),
                    'kind': 'actual',
                    'session': d.name,
                    'score': score_maps[d].get(idx),
                    'alignment': classify_alignment(idx, item['input'], d, base.name),
                    'summary': summarize(text),
                    'features': features(text),
                })
            for suffix in ['rerun_actual_output.txt', 'rerun2_actual_output.txt']:
                p = d / f'case_{idx}_{suffix}'
                if p.exists():
                    text = read_text(p)
                    item['candidates'].append({
                        'file': str(p),
                        'kind': suffix.replace('_actual_output.txt', ''),
                        'session': d.name,
                        'score': None,
                        'alignment': classify_alignment(idx, item['input'], d, p.name),
                        'summary': summarize(text),
                        'features': features(text),
                    })

        report.append(item)

    out = Path(args.output_json)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✅ 已写出: {out}', flush=True)
    print(f'✅ case 数: {len(report)}', flush=True)


if __name__ == '__main__':
    main()
