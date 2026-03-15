#!/usr/bin/env python3
"""
Log Converter for JSONL Transcript format.
Adapts simple JSONL transcripts (role/content) to ShareGPT format.
"""

import json
import argparse
import sys
import os
from datetime import datetime

def convert_jsonl_to_sharegpt(input_file, output_file):
    conversations = []
    query = ""
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line: {line[:50]}...")
                    continue
                
                role = entry.get('role', '')
                content = entry.get('content', '')
                
                if role == 'user':
                    sharegpt_role = 'human'
                    if not query:
                        query = content
                elif role == 'assistant':
                    sharegpt_role = 'gpt'
                elif role == 'system':
                    sharegpt_role = 'system'
                else:
                    sharegpt_role = role  # Fallback for other roles like 'tool'
                
                conversations.append({
                    "from": sharegpt_role,
                    "value": content
                })
                
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    # Metadata extraction (basic fallback)
    metadata = {
        "agent_name": "evalooper_agent",
        "platform": "evalooper",
        "timestamp": datetime.now().isoformat(),
        "config_file": "unknown",
        "query": query
    }

    output_data = {
        "conversations": conversations,
        "metadata": metadata
    }

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully converted '{input_file}' to '{output_file}'")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSONL transcript to ShareGPT format.")
    parser.add_argument("--input", required=True, help="Input JSONL file path")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    
    args = parser.parse_args()
    
    convert_jsonl_to_sharegpt(args.input, args.output)
