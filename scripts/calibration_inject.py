#!/usr/bin/env python3
"""
Calibration Review 注入工具 — 将 calibration_report.json 注入 HTML 可视化模板

用法:
    ./venv/bin/python scripts/calibration_inject.py <calibration_report.json路径>
    
产出:
    在同目录生成 calibration_review_view.html 并用浏览器打开
"""

import json
import os
import sys
import subprocess
import platform as pf

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def main():
    if len(sys.argv) < 2:
        print("❌ 用法: ./venv/bin/python scripts/calibration_inject.py <calibration_report.json路径>")
        sys.exit(1)

    report_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(report_path):
        print(f"❌ 找不到: {report_path}")
        sys.exit(1)

    print(f"1️⃣ 读取 calibration_report.json...", flush=True)
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "calibration_review.html")
    if not os.path.exists(template_path):
        print(f"❌ 找不到 HTML 模板: {template_path}")
        sys.exit(1)

    print(f"2️⃣ 注入数据到 HTML...", flush=True)
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    data_json = json.dumps(report, ensure_ascii=False, indent=2)
    injected_html = html.replace(
        "window.__CALIBRATION_DATA__ = null;",
        f"window.__CALIBRATION_DATA__ = {data_json};"
    )

    output_path = os.path.join(os.path.dirname(report_path), "calibration_review_view.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(injected_html)

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ 已生成: {output_path}")
    print(f"   大小: {file_size_kb:.1f} KB")

    print(f"3️⃣ 打开浏览器...", flush=True)
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

    print(f"\n✅ 完成！逐条审阅诊断结果，做出决策后点击「导出 decisions.json」。")


if __name__ == "__main__":
    main()
