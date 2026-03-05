#!/usr/bin/env python3
"""
Evalooper JSONL Transcript -> ShareGPT Format Converter

Adapted format: Evalooper JSONL transcript files (from iterative optimization workflow)
Format characteristics:
- Each line is a standalone JSON object (JSONL)
- Records have a "role" field: "user", "assistant", "tool"
- "user" role: contains "content" field with the user query -> mapped to "human"
- "assistant" role: contains "content" field with agent's text response -> mapped to "gpt"
- "tool" role: contains "name" (tool name) and "result" (tool output) fields
  -> mapped to "tool_response" with tool name annotation

Usage:
    python3 log_converter_evalooper_jsonl.py --input <input.jsonl> --output <output.json> [--agent-name <name>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_evalooper_jsonl(input_path: str, agent_name: str = "unknown") -> dict:
    """Parse evalooper JSONL transcript file with role/content/name/result fields."""
    lines = Path(input_path).read_text(encoding="utf-8").strip().splitlines()

    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    conversations = []
    metadata = {
        "agent_name": agent_name,
        "platform": "evalooper-jsonl",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_file": "",
        "query": "",
    }

    # Role mapping for ShareGPT format
    role_mapping = {
        "user": "human",
        "assistant": "gpt",
        "system": "system",
        "tool": "tool_response",
        "tool_call": "tool_call",
    }

    for rec in records:
        role = rec.get("role", "")
        
        # Handle tool records specially
        if role == "tool":
            tool_name = rec.get("name", "unknown_tool")
            tool_result = rec.get("result", "")
            
            # Skip empty tool results
            if not tool_result:
                continue
            
            # For tool_response, we include both the tool name and result
            # Format: [Tool: tool_name]\nresult
            conversations.append({
                "from": "tool_response",
                "value": f"[Tool: {tool_name}]\n{tool_result}"
            })
            continue
        
        # Handle other roles (user, assistant, system, tool_call)
        content = rec.get("content", "")
        
        # Skip empty content
        if not content or not isinstance(content, str):
            continue

        # Map role to ShareGPT format
        from_role = role_mapping.get(role, role)

        # Extract first user message as query
        if role == "user" and not metadata["query"]:
            metadata["query"] = content.strip()

        conversations.append({
            "from": from_role,
            "value": content.strip()
        })

    return {
        "conversations": conversations,
        "metadata": metadata
    }


def main():
    parser = argparse.ArgumentParser(description="Convert evalooper JSONL transcript to ShareGPT format")
    parser.add_argument("--input", required=True, help="Path to input JSONL file")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Name of the agent being tested")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = parse_evalooper_jsonl(args.input, agent_name=args.agent_name)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
