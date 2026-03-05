#!/usr/bin/env python3
"""
Claude Code JSONL Transcript -> ShareGPT JSON Converter

Adapted format: Claude Code JSONL transcript (.output files)
Format features:
  - Each line is a JSON object with fields: type, message, uuid, parentUuid, timestamp
  - type values: "user", "assistant", "progress"
  - "user" type with message.role=="user" and message.content as string = human turn
  - "user" type with message.role=="user" and message.content as list of tool_result = tool response
  - "assistant" type with message.content list of {"type":"text"} = gpt text
  - "assistant" type with message.content list of {"type":"tool_use"} = tool call
  - "progress" type = skip (internal events)

Usage:
    python3 jsonl_converter_claudecode.py --input <path>.output --output <path>.json
                                          [--agent-name <name>]

Output ShareGPT schema:
  {
    "conversations": [
      {"from": "human",         "value": "..."},
      {"from": "gpt",           "value": "..."},
      {"from": "tool_call",     "value": "{\"name\":\"...\",\"arguments\":{...}}"},
      {"from": "tool_response", "value": "..."}
    ],
    "metadata": { ... }
  }
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone


def parse_jsonl(path: Path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping malformed line: {e}", file=sys.stderr)
    return records


def extract_text_content(content_list):
    """Extract all text blocks from a content list into a single string."""
    parts = []
    for block in content_list:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(p for p in parts if p)


def extract_tool_calls(content_list):
    """Return list of tool_use blocks."""
    return [b for b in content_list if isinstance(b, dict) and b.get("type") == "tool_use"]


def extract_tool_results(content_list):
    """Return list of tool_result blocks."""
    return [b for b in content_list if isinstance(b, dict) and b.get("type") == "tool_result"]


def convert(records, agent_name: str = "my-agent"):
    conversations = []
    metadata = {
        "agent_name": agent_name,
        "platform": "claude-code-jsonl",
        "timestamp": "",
        "session_id": "",
        "query": "",
    }

    # Collect session-level metadata from the first record
    if records:
        first = records[0]
        metadata["session_id"] = first.get("sessionId", "")
        metadata["timestamp"] = first.get("timestamp", "")

    # We need to reconstruct conversation order.
    # Claude Code JSONL has a tree structure (parentUuid).
    # For linear conversations, records follow a chain:
    # human -> assistant(text) -> assistant(tool_call) -> user(tool_result) -> ...
    #
    # Strategy: iterate in file order (which is already chronological),
    # and group consecutive assistant records that share the same message id
    # into a single turn (text + tool_calls emitted together).

    i = 0
    while i < len(records):
        rec = records[i]
        rec_type = rec.get("type")

        # Skip internal/progress records
        if rec_type == "progress":
            i += 1
            continue

        msg = rec.get("message", {})
        role = msg.get("role", "")

        # ---- Human turn (initial user message, string content) ----
        if rec_type == "user" and isinstance(msg.get("content"), str):
            human_text = msg["content"].strip()
            if human_text:
                conversations.append({"from": "human", "value": human_text})
                if not metadata["query"]:
                    metadata["query"] = human_text
            i += 1
            continue

        # ---- Tool result turn (user type, list content with tool_result) ----
        if rec_type == "user" and isinstance(msg.get("content"), list):
            results = extract_tool_results(msg["content"])
            for result in results:
                result_content = result.get("content", [])
                # content can be a list of {type, text} or a string
                if isinstance(result_content, str):
                    result_text = result_content
                elif isinstance(result_content, list):
                    result_text = extract_text_content(result_content)
                else:
                    result_text = str(result_content)
                conversations.append({"from": "tool_response", "value": result_text})
            i += 1
            continue

        # ---- Assistant turn ----
        if rec_type == "assistant":
            content_list = msg.get("content", [])
            if not isinstance(content_list, list):
                i += 1
                continue

            # Collect all assistant records sharing the same message id
            # (Claude Code streams individual content blocks as separate JSONL lines)
            msg_id = msg.get("id", "")
            collected_text_parts = []
            collected_tool_calls = []

            j = i
            while j < len(records):
                r = records[j]
                if r.get("type") != "assistant":
                    break
                m = r.get("message", {})
                if msg_id and m.get("id", "") != msg_id:
                    break
                cl = m.get("content", [])
                if not isinstance(cl, list):
                    j += 1
                    continue
                for block in cl:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        collected_text_parts.append(block["text"].strip())
                    elif block.get("type") == "tool_use":
                        collected_tool_calls.append(block)
                j += 1

            # Emit gpt text if any
            combined_text = "\n".join(collected_text_parts).strip()
            if combined_text:
                conversations.append({"from": "gpt", "value": combined_text})

            # Emit tool_call entries
            for tc in collected_tool_calls:
                tool_entry = json.dumps(
                    {"name": tc.get("name", ""), "arguments": tc.get("input", {})},
                    ensure_ascii=False,
                )
                conversations.append({"from": "tool_call", "value": tool_entry})

            i = j
            continue

        # Fallback: skip unhandled record types
        i += 1

    return {"conversations": conversations, "metadata": metadata}


def main():
    parser = argparse.ArgumentParser(description="Convert Claude Code JSONL transcript to ShareGPT JSON")
    parser.add_argument("--input", required=True, help="Path to .output JSONL file")
    parser.add_argument("--output", required=True, help="Path to output .json file")
    parser.add_argument("--agent-name", default="my-agent", help="Agent name for metadata")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    records = parse_jsonl(input_path)
    if not records:
        print(f"[ERROR] Input file is empty or unreadable: {input_path}", file=sys.stderr)
        sys.exit(1)

    result = convert(records, agent_name=args.agent_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Wrote {len(result['conversations'])} conversation entries to {output_path}")


if __name__ == "__main__":
    main()
