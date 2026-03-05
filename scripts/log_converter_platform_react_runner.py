#!/usr/bin/env python3
"""
Platform React Runner stdout -> ShareGPT Format Converter

Adapted format: platform_react_runner stdout output (execution_log.txt)
Format characteristics:
- Node boundaries marked by: ============================================================ (60+ '=')
- Node name line: "  Node: <name>" (two leading spaces)
- Block end marker: ──────────────────────────────────────────────────────────────
  (long dash line, Unicode U+2500 or ASCII '-')
- Node: agent  -> may contain one or more:
    "  [Tool Call]: ToolName(){args}" -> mapped to tool_call (multi-line JSON supported)
    plain text (no [Tool Call]) -> mapped to gpt
- Node: tools  -> contains one or more <data type="json">...</data> tags -> each mapped to tool_response
- Node: tool_responses_summary -> content mapped to gpt (annotated summary)
- Node: condense -> skipped (internal)
- Node: agent_tool_call_check -> skipped (routing)
- Node: todo_list_update -> skipped (internal)
- Preamble lines (Python warnings, INFO logs before first Node) are discarded
- System prompt extracted from config_snapshot.yaml prompts.custom_system_prompt field
- Query extracted from query.txt in the case directory

NOTE: A single agent node block may contain multiple [Tool Call] entries (parallel tool calls).
      Tool call arguments may span multiple lines (formatted JSON). Both are handled correctly.
      A single tools node block may contain multiple <data type="json"> tags (parallel responses).
      Each tag is emitted as a separate tool_response turn.

Usage:
    python3 log_converter_platform_react_runner.py \\
        --input <execution_log.txt> \\
        --output <run_log.json> \\
        [--agent-name <name>] \\
        [--query-file <query.txt>] \\
        [--config-file <config_snapshot.yaml>]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKIP_NODES = {"condense", "todo_list_update", "agent_tool_call_check"}

RE_NODE_HEADER = re.compile(r"^={50,}\s*$")
RE_NODE_NAME   = re.compile(r"^\s+Node:\s+(\S+)\s*$")
RE_BLOCK_END   = re.compile(r"^[\u2500\u2501\-]{30,}\s*$")
RE_DATA_TAG    = re.compile(r"<data[^>]*>([\s\S]*?)</data>", re.DOTALL)
RE_LOG_TS      = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


# ---------------------------------------------------------------------------
# Block splitting
# ---------------------------------------------------------------------------

def split_into_blocks(lines: list) -> list:
    """
    Split raw lines into node blocks: [{"node": str, "lines": [str, ...]}, ...]
    Lines before the first node header (preamble) are discarded.
    """
    blocks = []
    current_node = None
    current_lines = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Detect 3-line node header pattern: ===... / "  Node: name" / ===...
        if RE_NODE_HEADER.match(line):
            if i + 1 < n and RE_NODE_NAME.match(lines[i + 1]):
                nm = RE_NODE_NAME.match(lines[i + 1])
                if i + 2 < n and RE_NODE_HEADER.match(lines[i + 2]):
                    # Flush previous block
                    if current_node is not None:
                        blocks.append({"node": current_node, "lines": current_lines})
                    current_node = nm.group(1).strip()
                    current_lines = []
                    i += 3
                    continue

        # Block-end separator — discard the line, don't include in content
        if RE_BLOCK_END.match(line):
            i += 1
            continue

        # Accumulate content lines for the current node
        if current_node is not None:
            current_lines.append(line)

        i += 1

    # Flush last block
    if current_node is not None:
        blocks.append({"node": current_node, "lines": current_lines})

    return blocks


# ---------------------------------------------------------------------------
# Tool call parsing (handles multi-line JSON arguments)
# ---------------------------------------------------------------------------

def parse_agent_block(lines: list) -> list:
    """
    Parse all tool_call and gpt turns from an agent node block.

    A single agent block may contain multiple parallel [Tool Call] entries.
    Tool call arguments may be formatted across multiple lines (indented JSON).

    Strategy:
    1. Join all lines into one text blob.
    2. Walk the text finding each [Tool Call]: marker.
    3. Use balanced-brace counting to extract the full JSON argument object,
       even when it spans multiple lines.
    4. Any text between tool calls (or before the first one) that is non-empty
       after stripping is emitted as a gpt turn.

    Returns list of {"from": str, "value": str} dicts.
    """
    text = "\n".join(lines)
    turns = []

    # Pattern to find [Tool Call]: ToolName()
    CALL_MARKER_RE = re.compile(r"\[Tool Call\]:\s*(\w[\w.]*)\s*\(\s*\)")

    pos = 0
    for m in CALL_MARKER_RE.finditer(text):
        # Emit any text before this tool call as gpt (if non-empty)
        preceding = text[pos:m.start()].strip()
        if preceding:
            turns.append({"from": "gpt", "value": preceding})

        tool_name = m.group(1)
        after_paren = text[m.end():].lstrip()

        # Check if there's a JSON object following the ()
        if after_paren.startswith("{"):
            # Find the balanced closing brace
            depth = 0
            end_offset = 0
            for ci, ch in enumerate(after_paren):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_offset = ci + 1
                        break
            json_str = after_paren[:end_offset]
            try:
                arguments = json.loads(json_str)
            except json.JSONDecodeError:
                # Compact whitespace and retry
                compact = re.sub(r'\s+', ' ', json_str).strip()
                try:
                    arguments = json.loads(compact)
                except json.JSONDecodeError:
                    arguments = {"_raw": json_str.strip()}
            # Advance pos past the consumed JSON
            pos = m.end() + (len(text) - len(text[m.end():])) + end_offset
            # Compute absolute position of end of JSON in text
            abs_json_end = m.end() + (len(text[m.end():]) - len(text[m.end():].lstrip())) + end_offset
            pos = abs_json_end
        else:
            arguments = {}
            pos = m.end()

        turns.append({
            "from": "tool_call",
            "value": json.dumps({"name": tool_name, "arguments": arguments}, ensure_ascii=False),
        })

    # Emit any trailing text after the last tool call
    trailing = text[pos:].strip()
    if trailing:
        turns.append({"from": "gpt", "value": trailing})

    # If no tool calls were found, entire block is gpt text
    if not turns:
        body = text.strip()
        if body:
            turns.append({"from": "gpt", "value": body})

    return turns


# ---------------------------------------------------------------------------
# Tool response parsing (handles multiple <data> tags)
# ---------------------------------------------------------------------------

def parse_tools_block(lines: list) -> list:
    """
    Extract all tool responses from a tools node block.

    A single tools block may contain multiple <data type="json">...</data> tags
    (one per parallel tool call). Each tag is emitted as a separate tool_response turn.

    Returns list of {"from": "tool_response", "value": str} dicts.
    """
    body = "\n".join(lines).strip()
    data_matches = RE_DATA_TAG.findall(body)

    if data_matches:
        return [{"from": "tool_response", "value": raw.strip()} for raw in data_matches]

    # Fallback: no <data> tags found, return entire body as one response
    if body:
        return [{"from": "tool_response", "value": body}]
    return []


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def extract_timestamp(raw_text: str) -> str:
    m = RE_LOG_TS.search(raw_text)
    if m:
        return m.group(1)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_query(query_file) -> str:
    if query_file:
        p = Path(query_file)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return ""


def load_config_meta(config_file) -> tuple:
    """Returns (system_prompt: str, config_file_name: str, platform: str, model: str)."""
    if not config_file:
        return "", "", "platform_react_runner", ""
    p = Path(config_file)
    if not p.exists():
        return "", p.name, "platform_react_runner", ""

    text = p.read_text(encoding="utf-8")
    config_name = p.name

    # Extract model
    model_m = re.search(r'^\s+model:\s+"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    model = model_m.group(1).strip() if model_m else ""

    # Extract platform (graph name)
    graph_m = re.search(r'^\s+name:\s+"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    platform = graph_m.group(1).strip() if graph_m else "platform_react_runner"

    # Extract system prompt via YAML library if available, else regex
    system_prompt = ""
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text)
        prompts = data.get("prompts", {}) if isinstance(data, dict) else {}
        if isinstance(prompts, dict):
            system_prompt = prompts.get("custom_system_prompt", "") or ""
    except Exception:
        # Fallback: regex extraction of pipe-block scalar
        key_re = re.compile(r"^(\s*)custom_system_prompt:\s*\|[-]?\s*$", re.MULTILINE)
        km = key_re.search(text)
        if km:
            base_indent = len(km.group(1)) + 2
            lines = text.splitlines()
            start_idx = text[:km.start()].count("\n") + 1
            collected = []
            for sl in lines[start_idx:]:
                if not sl.strip():
                    collected.append("")
                    continue
                cur_indent = len(sl) - len(sl.lstrip())
                if cur_indent < base_indent:
                    break
                collected.append(sl[base_indent:])
            while collected and not collected[-1].strip():
                collected.pop()
            system_prompt = "\n".join(collected)

    return system_prompt.strip(), config_name, platform, model


# ---------------------------------------------------------------------------
# Conversation building
# ---------------------------------------------------------------------------

def build_conversations(blocks: list) -> list:
    conversations = []

    for block in blocks:
        node = block["node"]
        content_lines = block["lines"]

        if node in SKIP_NODES:
            continue

        # Strip leading/trailing blank lines
        while content_lines and not content_lines[0].strip():
            content_lines = content_lines[1:]
        while content_lines and not content_lines[-1].strip():
            content_lines = content_lines[:-1]

        if node == "agent":
            turns = parse_agent_block(content_lines)
            conversations.extend(turns)

        elif node == "tools":
            turns = parse_tools_block(content_lines)
            conversations.extend(turns)

        elif node == "tool_responses_summary":
            summary = "\n".join(content_lines).strip()
            if summary:
                conversations.append({"from": "gpt", "value": summary})

        # All other nodes: skip silently

    return conversations


# ---------------------------------------------------------------------------
# Main conversion entry point
# ---------------------------------------------------------------------------

def convert(
    input_path: str,
    agent_name: str = "unknown",
    query_file=None,
    config_file=None,
) -> dict:
    raw_text = Path(input_path).read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    timestamp = extract_timestamp(raw_text)
    query = load_query(query_file)
    system_prompt, config_name, platform, model = load_config_meta(config_file)

    blocks = split_into_blocks(lines)
    conversations = build_conversations(blocks)

    # Prepend system + human turns at the front
    prefix = []
    if system_prompt:
        prefix.append({"from": "system", "value": system_prompt})
    if query:
        prefix.append({"from": "human", "value": query})

    conversations = prefix + conversations

    metadata = {
        "agent_name": agent_name,
        "platform": platform,
        "timestamp": timestamp,
        "config_file": config_name,
        "model": model,
        "query": query,
    }

    return {"conversations": conversations, "metadata": metadata}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert platform_react_runner execution_log.txt to ShareGPT JSON"
    )
    parser.add_argument("--input", required=True, help="Path to execution_log.txt")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Agent name")
    parser.add_argument("--query-file", default=None, help="Path to query.txt")
    parser.add_argument("--config-file", default=None, help="Path to config_snapshot.yaml")
    args = parser.parse_args()

    ip = Path(args.input)
    if not ip.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if ip.stat().st_size == 0:
        print(f"ERROR: Input file is empty: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = convert(
        input_path=args.input,
        agent_name=args.agent_name,
        query_file=args.query_file,
        config_file=args.config_file,
    )

    op = Path(args.output)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
