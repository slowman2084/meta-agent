import yaml
import os
import subprocess
import time

def run_case(case_index, input_text):
    print(f"=== Running Case {case_index} ===")
    
    # 构造 prompt
    prompt = f"""Task: 请为以下用户请求生成评分标准 (Rubrics)。

[用户]: {input_text}

Requirements: 生成一组原子化的评分条目。每个条目应包含分值 (points) 和清晰的描述。

请直接输出生成的评分标准。"""

    # 调用 Sub Agent (模拟 IDE 模式调用)
    # 这里我们使用一个临时的 python 脚本来通过 task 工具的思想逻辑进行调用，
    # 但在当前环境下，最稳妥的是我直接作为主控者逐个发起 task。
    # 所以这个脚本主要用于生成指令列表。
    
    return prompt

def main():
    testcases_path = "/Users/wenxinhuang/Documents/all_in_one/项目/meta-agent/source/meta-rubric-gen/testcases.yaml"
    with open(testcases_path, 'r') as f:
        data = yaml.safe_load(f)
    
    cases = data.get('cases', [])
    for i, case in enumerate(cases):
        input_text = case.get('Input', '')
        # 我们在这里只打印，实际执行由我通过 Task 逐个发起
        print(f"INDEX_{i}")
        print(input_text)
        print("-" * 20)

if __name__ == "__main__":
    main()
