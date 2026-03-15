import yaml
import json
import os
import re
from pathlib import Path
from datetime import datetime

def get_keywords(text):
    # Simple keyword extraction
    return set(re.findall(r'\w+', text.lower()))

def convert_to_sharegpt(log_dir, agent_name, start_case, end_case, testcases_path):
    # Load testcases
    with open(testcases_path, 'r', encoding='utf-8') as f:
        testcases_data = yaml.safe_load(f)
    
    testcases = testcases_data.get('cases', [])
    
    # Map testcases by index and content for matching
    # We will use the transcript content to match the input
    
    for i in range(start_case, end_case + 1):
        case_id = f"case_{i}"
        transcript_path = os.path.join(log_dir, f"{case_id}_transcript.jsonl")
        output_path = os.path.join(log_dir, f"{case_id}_actual_output.txt")
        target_path = os.path.join(log_dir, f"{case_id}_run_log.json")
        
        if not os.path.exists(transcript_path):
            print(f"Warning: {transcript_path} not found. Skipping.")
            continue
            
        # Read transcript to extract content for matching
        steps = []
        transcript_content = ""
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        step = json.loads(line)
                        steps.append(step)
                        # Collect text fields
                        for v in step.values():
                            if isinstance(v, str):
                                transcript_content += " " + v
        except Exception as e:
            print(f"Error reading {transcript_path}: {e}")
            continue

        # Match with testcases
        best_match = None
        best_score = -1
        
        transcript_keywords = get_keywords(transcript_content)
        
        for idx, tc in enumerate(testcases):
            tc_input = tc.get('Input', '')
            tc_keywords = get_keywords(tc_input)
            if not tc_keywords: continue
            
            # Simple Jaccard-like score or intersection count
            score = len(transcript_keywords.intersection(tc_keywords))
            if score > best_score:
                best_score = score
                best_match = tc
        
        if not best_match:
            print(f"Error: Could not find matching testcase for {case_id}")
            case_input = "Unknown Query"
        else:
            case_input = best_match.get('Input', 'Unknown Query')

        # Read actual output
        actual_output = ""
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                actual_output = f.read().strip()
        
        # Build conversations
        conversations = []
        conversations.append({
            "from": "human",
            "value": case_input.strip()
        })
        
        # Format reasoning
        reasoning_text = "Internal Reasoning Steps:\n"
        for step in steps:
            step_str = f"- Step {step.get('step', '?')} ({step.get('action', 'Unknown')}): "
            details = []
            for k, v in step.items():
                if k not in ['step', 'action']:
                    details.append(f"{k}={v}")
            step_str += ", ".join(details)
            reasoning_text += step_str + "\n"
            
        gpt_value = reasoning_text.strip() + "\n\nFinal Output:\n" + actual_output
        conversations.append({
            "from": "gpt",
            "value": gpt_value.strip()
        })
        
        # Metadata
        metadata = {
            "agent_name": agent_name,
            "platform": "evalooper-transcript",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "case_id": case_id,
            "query": case_input.strip()[:100] + "..." if len(case_input) > 100 else case_input.strip()
        }
        
        result = {
            "conversations": conversations,
            "metadata": metadata
        }
        
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully converted {case_id} to {target_path} (Matched score: {best_score})")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_dir", required=True)
    parser.add_argument("--agent_name", required=True)
    parser.add_argument("--start", type=int, default=12)
    parser.add_argument("--end", type=int, default=23)
    parser.add_argument("--testcases", required=True)
    args = parser.parse_args()
    
    convert_to_sharegpt(args.log_dir, args.agent_name, args.start, args.end, args.testcases)
