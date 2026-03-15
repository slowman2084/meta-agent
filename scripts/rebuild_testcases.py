import json
import yaml
import os

def rebuild():
    source_file = "/Users/wenxinhuang/Documents/all_in_one/项目/meta-agent/source/meta-rubric-gen/tmp_cases.jsonl"
    output_file = "/Users/wenxinhuang/Documents/all_in_one/项目/meta-agent/source/meta-rubric-gen/testcases.yaml"
    bak_file = output_file + ".corrupted.bak"

    if os.path.exists(output_file):
        os.rename(output_file, bak_file)
        print(f"Backed up corrupted YAML to {bak_file}")

    new_cases = []
    with open(source_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            
            # 提取 Input
            # prompt 是一个列表，通常包含 [{"content": "...", "role": "user"}]
            user_input = ""
            for msg in data.get('prompt', []):
                if msg.get('role') == 'user':
                    # 构造与任务一致的格式
                    user_input = f"Task: 请为以下用户请求生成评分标准 (Rubrics)。\n\n[用户]: {msg.get('content')}\n\nRequirements: 生成一组原子化的评分条目。每个条目应包含分值 (points) 和清晰的描述。"
                    break
            
            # 提取 ExpectedOutput (即原始的 rubrics)
            expected = data.get('rubrics', [])
            
            new_cases.append({
                "Input": user_input,
                "ExpectedOutput": expected,
                "Judge": "请确保评分条目原子化，分值分配合理，涵盖安全性、准确性、完备性和呈现方式。"
            })

    final_data = {
        "meta": {
            "count": len(new_cases),
            "notice": "Rebuilt from healthy tmp_cases.jsonl to fix index shift."
        },
        "cases": new_cases
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(final_data, f, allow_unicode=True, sort_keys=False)
    
    print(f"Successfully rebuilt {len(new_cases)} cases in {output_file}")

if __name__ == "__main__":
    rebuild()
