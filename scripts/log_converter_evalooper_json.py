#!/usr/bin/env python3
"""
Evalooper JSON Transcript -> ShareGPT Format Converter

Adapted format: Evalooper JSON transcript files (single JSON array)
Format characteristics:
- The entire file is a JSON array of message objects.
- Each object has a "role" field: "user", "assistant", "tool"
- "user" role: contains "content" field -> mapped to "human"
- "assistant" role: 
    - "thought" field -> mapped to "gpt" (as reasoning)
    - "content" field -> mapped to "gpt" (as response)
    - "tool_calls" field -> each entry mapped to "tool_call"
- "tool" role: contains "content" field -> mapped to "tool_response"

Usage:
    python3 log_converter_evalooper_json.py --input <input.json> --output <output.json> [--agent-name <name>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_evalooper_json(input_path: str, agent_name: str = "unknown") -> dict:
    """Parse evalooper JSON transcript file (array of messages)."""
    try:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
        return {"conversations": [], "metadata": {"error": str(e)}}

    if not isinstance(data, list):
        print("ERROR: Input JSON is not a list", file=sys.stderr)
        return {"conversations": [], "metadata": {"error": "Not a list"}}

    conversations = []
    metadata = {
        "agent_name": agent_name,
        "platform": "evalooper-json",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_file": "",
        "query": "",
    }

    for msg in data:
        role = msg.get("role")
        
        if role == "user":
            content = msg.get("content", "")
            if not metadata["query"]:
                metadata["query"] = content
            conversations.append({
                "from": "human",
                "value": content
            })
            
        elif role == "assistant":
            thought = msg.get("thought", "")
            content = msg.get("content", "")
            
            # Combine thought and content for the gpt turn if both exist, 
            # or just use whichever is present.
            combined_value = ""
            if thought:
                combined_value += thought
            if content:
                if combined_value:
                    combined_value += "\n\n"
                combined_value += content
                
            if combined_value:
                conversations.append({
                    "from": "gpt",
                    "value": combined_value
                })
                
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                conversations.append({
                    "from": "tool_call",
                    "value": json.dumps(tc, ensure_ascii=False)
                })
                
        elif role == "tool":
            content = msg.get("content", "")
            # If there's a name, it's helpful to include it in the response
            name = msg.get("name", "")
            value = content
            if name:
                value = f"[Tool: {name}]\n{content}"
            
            conversations.append({
                "from": "tool_response",
                "value": value
            })

    return {
        "conversations": conversations,
        "metadata": metadata
    }


def main():
    parser = argparse.ArgumentParser(description="Convert evalooper JSON transcript to ShareGPT format")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Name of the agent being tested")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = parse_evalooper_json(args.input, agent_name=args.agent_name)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
