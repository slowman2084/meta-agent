#!/usr/bin/env python3
"""
Simple JSONL Transcript -> ShareGPT Format Converter

Adapted format: Simple JSONL transcript files
Format characteristics:
- Each line is a standalone JSON object (JSONL)
- Records have a "role" field: "user" or "assistant"
- Records have a "content" field containing the text
- "user" role -> mapped to "human" in ShareGPT
- "assistant" role -> mapped to "gpt" in ShareGPT

Usage:
    python3 log_converter_simple_jsonl.py --input <input.jsonl> --output <output.json> [--agent-name <name>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_simple_jsonl(input_path: str, agent_name: str = "unknown") -> dict:
    """Parse simple JSONL transcript file with role/content fields."""
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
        "platform": "simple-jsonl",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_file": "",
        "query": "",
    }

    # Role mapping
    role_mapping = {
        "user": "human",
        "assistant": "gpt",
        "system": "system",
        "tool": "tool_response",
        "tool_call": "tool_call",
    }

    for rec in records:
        role = rec.get("role", "")
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
    parser = argparse.ArgumentParser(description="Convert simple JSONL transcript to ShareGPT format")
    parser.add_argument("--input", required=True, help="Path to input JSONL file")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Name of the agent being tested")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = parse_simple_jsonl(args.input, agent_name=args.agent_name)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
