#!/usr/bin/env python3
"""
Claude Code JSONL Transcript -> ShareGPT Format Converter

Adapted format: Claude Code JSONL transcript (.output files)
Format characteristics:
- Each line is a standalone JSON object (JSONL)
- Records have a "type" field: "user", "assistant", "progress"
- "user" records contain message.role="user" with either text content (original query)
  or tool_result content (tool responses)
- "assistant" records contain message.role="assistant" with content array:
    - {"type": "text", "text": "..."} -> gpt turn
    - {"type": "tool_use", "id": "...", "name": "...", "input": {...}} -> tool_call turn
- "progress" records are skipped (internal events: mcp_progress, hook_progress)
- tool_result user records (sourceToolAssistantUUID present) are mapped to tool_response

Usage:
    python3 log_converter_claude_jsonl.py --input <input.output> --output <output.json> [--agent-name <name>]
"""

import argparse
import json
import sys
from pathlib import Path


def parse_jsonl_transcript(input_path: str, agent_name: str = "unknown") -> dict:
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
        "platform": "claude-code-jsonl",
        "timestamp": "",
        "config_file": "",
        "query": "",
        "session_id": "",
        "agent_id": "",
    }

    # Track tool_use id -> tool name for matching tool_responses
    tool_use_map: dict[str, str] = {}

    # We need to reconstruct conversation in order.
    # Strategy:
    #   1. Collect all assistant content blocks (text + tool_use) grouped by message id,
    #      preserving order of first appearance.
    #   2. User records that are tool_result responses map to tool_response turns.
    #   3. The very first user record without sourceToolAssistantUUID is the human query.

    # We'll do a two-pass approach:
    # Pass 1: collect tool_use id -> tool name from all assistant records
    for rec in records:
        if rec.get("type") == "assistant":
            msg = rec.get("message", {})
            for block in msg.get("content", []):
                if block.get("type") == "tool_use":
                    tool_use_map[block["id"]] = block.get("name", "unknown_tool")

    # Pass 2: build conversation in record order, deduplicate assistant message blocks
    # Multiple records can share the same message id (streaming chunks) - deduplicate
    seen_msg_ids: set = set()
    # We track (msg_id, block_index) to avoid duplicating individual content blocks
    seen_blocks: set = set()  # (msg_id, block_type, block_id_or_index)

    # Build ordered list of conversation turns
    # Each turn: {"from": ..., "value": ...}

    first_timestamp = ""

    for idx, rec in enumerate(records):
        rec_type = rec.get("type")
        ts = rec.get("timestamp", "")
        if ts and not first_timestamp:
            first_timestamp = ts

        # Skip progress events
        if rec_type == "progress":
            continue

        if rec_type == "user":
            msg = rec.get("message", {})
            content = msg.get("content", "")
            source_tool_uuid = rec.get("sourceToolAssistantUUID")

            # Case 1: plain text user message (the original human query)
            if isinstance(content, str) and content.strip():
                if not metadata["query"]:
                    metadata["query"] = content.strip()
                conversations.append({
                    "from": "human",
                    "value": content.strip()
                })

            # Case 2: list content -> could be tool_result(s)
            elif isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id", "")
                        tool_name = tool_use_map.get(tool_use_id, "unknown_tool")
                        # Extract text from content
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            parts = []
                            for c in result_content:
                                if c.get("type") == "text":
                                    parts.append(c.get("text", ""))
                            result_text = "\n".join(parts)
                        elif isinstance(result_content, str):
                            result_text = result_content
                        else:
                            result_text = str(result_content)

                        block_key = ("tool_result", tool_use_id)
                        if block_key not in seen_blocks:
                            seen_blocks.add(block_key)
                            conversations.append({
                                "from": "tool_response",
                                "value": result_text,
                                "_tool_name": tool_name,
                                "_tool_use_id": tool_use_id,
                            })

        elif rec_type == "assistant":
            msg = rec.get("message", {})
            msg_id = msg.get("id", "")
            content_blocks = msg.get("content", [])

            # Populate metadata from first assistant message
            if not metadata["session_id"]:
                metadata["session_id"] = rec.get("sessionId", "")
                metadata["agent_id"] = rec.get("agentId", "")

            for b_idx, block in enumerate(content_blocks):
                block_type = block.get("type")
                # Build dedup key
                if block_type == "tool_use":
                    dedup_key = ("assistant", "tool_use", block.get("id", f"{msg_id}_{b_idx}"))
                else:
                    dedup_key = ("assistant", block_type, msg_id, b_idx)

                if dedup_key in seen_blocks:
                    continue
                seen_blocks.add(dedup_key)

                if block_type == "text":
                    text = block.get("text", "").strip()
                    if text:
                        conversations.append({
                            "from": "gpt",
                            "value": text
                        })

                elif block_type == "tool_use":
                    tool_name = block.get("name", "unknown_tool")
                    tool_input = block.get("input", {})
                    conversations.append({
                        "from": "tool_call",
                        "value": json.dumps({
                            "name": tool_name,
                            "arguments": tool_input
                        }, ensure_ascii=False)
                    })

    # Clean up internal helper fields from tool_response
    clean_conversations = []
    for turn in conversations:
        clean_turn = {"from": turn["from"], "value": turn["value"]}
        clean_conversations.append(clean_turn)

    # Set metadata timestamp
    metadata["timestamp"] = first_timestamp

    return {
        "conversations": clean_conversations,
        "metadata": metadata
    }


def main():
    parser = argparse.ArgumentParser(description="Convert Claude Code JSONL transcript to ShareGPT format")
    parser.add_argument("--input", required=True, help="Path to input .output JSONL file")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Name of the agent being tested")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = parse_jsonl_transcript(args.input, agent_name=args.agent_name)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
