#!/usr/bin/env python3
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

"""
Log Converter for Step-Action JSONL format.
Used for: transcript.jsonl with fields like step, action, input, output, tool, args, result.
"""

def convert_step_action_to_sharegpt(input_file, agent_name="meta-rubric-gen"):
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: {input_file} not found")
        return None
    
    try:
        lines = input_path.read_text(encoding='utf-8').strip().splitlines()
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return None
    
    conversations = []
    metadata = {
        "agent_name": agent_name,
        "platform": "evalooper-step-action",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_file": "unknown",
        "query": ""
    }
    
    for i, line in enumerate(lines):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
            
        action = data.get("action", "")
        input_text = data.get("input", "")
        output_text = data.get("output", "")
        tool = data.get("tool")
        args = data.get("args")
        result = data.get("result")
        
        # 第一步通常包含用户输入
        if i == 0 and input_text:
            metadata["query"] = input_text
            conversations.append({"from": "human", "value": input_text})
        
        # 针对 Tool Call
        if tool and args:
            # 如果有前置思考或 output
            if output_text:
                conversations.append({"from": "gpt", "value": f"Thinking: {action}\n{output_text}"})
                
            conversations.append({
                "from": "tool_call",
                "value": json.dumps({"name": tool, "arguments": args}, ensure_ascii=False)
            })
            if result:
                conversations.append({
                    "from": "tool_response",
                    "value": str(result)
                })
        else:
            # 普通 AI 输出或分析步骤
            if output_text:
                conversations.append({
                    "from": "gpt",
                    "value": f"[{action}]\n{output_text}"
                })
            elif input_text and i > 0:
                conversations.append({
                    "from": "gpt",
                    "value": f"[{action}] Input: {input_text}"
                })

    return {
        "conversations": conversations,
        "metadata": metadata
    }

def main():
    parser = argparse.ArgumentParser(description="Convert step-action JSONL to ShareGPT JSON")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--agent-name", default="meta-rubric-gen", help="Agent name")
    args = parser.parse_args()

    result = convert_step_action_to_sharegpt(args.input, args.agent_name)
    if result:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Successfully converted {args.input} to {args.output}")
    else:
        print(f"Failed to convert {args.input}")
        sys.exit(1)

if __name__ == "__main__":
    main()
