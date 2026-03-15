import yaml
import json
import os

def prepare_eval_data():
    base_dir = "/Users/wenxinhuang/Documents/all_in_one/项目/meta-agent/source/meta-rubric-gen/"
    iter_dir = os.path.join(base_dir, "tmp/evalooper/iter_1/")
    testcases_path = os.path.join(base_dir, "testcases.yaml")
    output_dir = os.path.join(iter_dir, "eval_packets")
    os.makedirs(output_dir, exist_ok=True)

    with open(testcases_path, 'r') as f:
        data = yaml.safe_load(f)
    
    cases = data.get('cases', [])
    for i, case in enumerate(cases):
        # 构造评估数据包
        packet = {
            "index": i,
            "Input": case.get('Input'),
            "ExpectedOutput": case.get('ExpectedOutput'),
            "Judge": case.get('Judge'),
            "ActualOutput": "",
            "RunLog": {}
        }
        
        # 读取实际产物
        actual_path = os.path.join(iter_dir, f"case_{i}_actual_output.txt")
        log_path = os.path.join(iter_dir, f"case_{i}_run_log.json")
        
        if os.path.exists(actual_path):
            with open(actual_path, 'r') as f:
                packet["ActualOutput"] = f.read()
        
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                packet["RunLog"] = json.load(f)
        
        # 写入数据包
        with open(os.path.join(output_dir, f"packet_{i}.json"), 'w', encoding='utf-8') as f:
            json.dump(packet, f, ensure_ascii=False, indent=2)
    
    print(f"Prepared {len(cases)} evaluation packets in {output_dir}")

if __name__ == "__main__":
    prepare_eval_data()
