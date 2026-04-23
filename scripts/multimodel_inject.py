#!/usr/bin/env python3
"""
多模型对比工具 — 将 manifest.json + result.md + sharegpt.json 注入 HTML 模板

用法:
    ./venv/bin/python scripts/multimodel_inject.py <manifest.json路径>
    
产出:
    在 manifest.json 同目录生成 multimodel_compare_view.html 并用浏览器打开

数据注入:
    - result_content: 从 result.md 文件读取 Markdown 内容
    - sharegpt_conversations: 从 sharegpt.json 文件读取对话记录（含 tool calls）
    - case_inputs: 从 inputs.json 或 manifest 中提取每条用例的 Input
"""

import json
import os
import sys
import subprocess
import platform as pf

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def load_json_safe(path):
    """安全加载 JSON 文件，失败返回 None"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"   ⚠️ 读取失败: {path} ({e})", flush=True)
        return None


def extract_case_inputs(base_dir, manifest):
    """
    从 inputs.json 或 manifest 中提取每条用例的 Input 文本。
    返回 { case_id: input_text }
    """
    inputs_map = {}

    # 尝试读取 inputs.json
    inputs_path = os.path.join(base_dir, "inputs.json")
    if os.path.exists(inputs_path):
        inputs_data = load_json_safe(inputs_path)
        if isinstance(inputs_data, list):
            for i, item in enumerate(inputs_data):
                case_id = f"case_{i}"
                if isinstance(item, dict):
                    inputs_map[case_id] = item.get("Input", item.get("input", json.dumps(item, ensure_ascii=False)))
                elif isinstance(item, str):
                    inputs_map[case_id] = item
        elif isinstance(inputs_data, dict):
            for k, v in inputs_data.items():
                if isinstance(v, dict):
                    inputs_map[k] = v.get("Input", v.get("input", json.dumps(v, ensure_ascii=False)))
                else:
                    inputs_map[k] = str(v)

    # 如果 manifest 中有 case_inputs 字段，直接使用（覆盖）
    if "case_inputs" in manifest and isinstance(manifest["case_inputs"], dict):
        inputs_map.update(manifest["case_inputs"])

    return inputs_map


def main():
    if len(sys.argv) < 2:
        print("❌ 用法: ./venv/bin/python scripts/multimodel_inject.py <manifest.json路径>")
        sys.exit(1)

    manifest_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(manifest_path):
        print(f"❌ 找不到 manifest.json: {manifest_path}")
        sys.exit(1)

    print("=" * 60, flush=True)
    print("多模型对比工具 — 数据注入", flush=True)
    print("=" * 60, flush=True)

    # 1. 读取 manifest
    print(f"\n1️⃣ 读取 manifest.json...", flush=True)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    base_dir = os.path.dirname(manifest_path)
    results = manifest.get("results", [])
    print(f"   {len(results)} 份结果", flush=True)

    # 2. 读取 result.md 内容
    print(f"\n2️⃣ 读取 result.md 文件...", flush=True)
    loaded_results = 0
    for entry in results:
        result_file = entry.get("result_file", "")
        result_path = os.path.join(base_dir, result_file)
        if os.path.exists(result_path):
            with open(result_path, "r", encoding="utf-8") as f:
                entry["result_content"] = f.read()
            loaded_results += 1
        else:
            entry["result_content"] = f"⚠️ 文件不存在: {result_file}"
    print(f"   ✅ 加载了 {loaded_results}/{len(results)} 份", flush=True)

    # 3. 读取 sharegpt.json（对话记录，含 tool calls）
    print(f"\n3️⃣ 读取 sharegpt.json 文件...", flush=True)
    loaded_sharegpt = 0
    for entry in results:
        sharegpt_file = entry.get("sharegpt_file", "")
        if not sharegpt_file:
            # 自动推断文件名: model_runN_caseM_sharegpt.json
            result_file = entry.get("result_file", "")
            sharegpt_file = result_file.replace("_result.md", "_sharegpt.json")

        sharegpt_path = os.path.join(base_dir, sharegpt_file)
        if os.path.exists(sharegpt_path):
            sgdata = load_json_safe(sharegpt_path)
            if sgdata:
                convs = sgdata.get("conversations", [])
                entry["sharegpt_conversations"] = convs
                loaded_sharegpt += 1
                tool_calls = sum(1 for c in convs if c.get("from") == "tool_call")
                if tool_calls > 0:
                    print(f"   [{entry.get('model','?')}/run{entry.get('run','?')}/{entry.get('case_id','?')}] "
                          f"{len(convs)} turns, {tool_calls} tool calls ✅", flush=True)
            else:
                entry["sharegpt_conversations"] = []
        else:
            entry["sharegpt_conversations"] = []

    print(f"   ✅ 加载了 {loaded_sharegpt}/{len(results)} 份 ShareGPT 数据", flush=True)

    # 4. 提取 case inputs
    print(f"\n4️⃣ 提取 Input 数据...", flush=True)
    case_inputs = extract_case_inputs(base_dir, manifest)
    manifest["case_inputs"] = case_inputs
    print(f"   ✅ {len(case_inputs)} 条 Input", flush=True)

    # 5. 注入到 HTML
    print(f"\n5️⃣ 注入数据到 HTML...", flush=True)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "multimodel_compare.html")
    if not os.path.exists(template_path):
        print(f"❌ 找不到 HTML 模板: {template_path}")
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    data_json = json.dumps(manifest, ensure_ascii=False, indent=2)
    injected_html = html.replace(
        "window.__MULTIMODEL_DATA__ = null;",
        f"window.__MULTIMODEL_DATA__ = {data_json};"
    )

    output_path = os.path.join(base_dir, "multimodel_compare_view.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(injected_html)

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"   ✅ 已生成: {output_path}")
    print(f"   大小: {file_size_kb:.1f} KB", flush=True)

    # 6. 打开浏览器
    print(f"\n6️⃣ 打开浏览器...", flush=True)
    try:
        if pf.system() == "Darwin":
            subprocess.run(["open", output_path], check=True)
        elif pf.system() == "Linux":
            subprocess.run(["xdg-open", output_path], check=True)
        else:
            print(f"   请手动打开: {output_path}")
    except Exception as e:
        print(f"   浏览器打开失败: {e}")
        print(f"   请手动打开: {output_path}")

    print(f"\n" + "=" * 60)
    print(f"✅ 完成！")
    print(f"   - 📄 Output 对比: 查看渲染后的最终输出")
    print(f"   - 🔧 Tools 对比:  查看每个模型的 tool 调用过程")
    print(f"   - 为每个用例选择最佳输出 → 点击「导出 JSON」")
    print(f"=" * 60)


if __name__ == "__main__":
    main()
