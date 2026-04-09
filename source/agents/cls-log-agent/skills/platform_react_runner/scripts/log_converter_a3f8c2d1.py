#!/usr/bin/env python3
"""
log_converter_a3f8c2d1.py — Platform stdout log -> ShareGPT JSON converter
============================================================================
Adapted log format characteristics:
  - Node boundary markers:
      ============================================================
        Node: <name>
      ============================================================
  - End-of-node separator (optional, single line):
      ────────────────────────────────────────────────────────────
  - Tool call lines inside Node: agent start with:
      [Tool Call]: <FunctionName>(){<json-body>}
  - AI text responses inside Node: agent have NO special prefix
    (any non-tool-call, non-empty content is treated as AI text)
  - Node: tools content is the raw tool return value (may be
    wrapped in <data type="json">...</data>)
  - Node: tool_responses_summary content is a gpt summary turn
  - Skipped nodes: condense, agent_tool_call_check, todo_list_update

Usage:
    python3 log_converter_a3f8c2d1.py --input execution_log.txt \
        --output run_log.json \
        [--query query.txt] \
        [--config config_snapshot.yaml] \
        [--agent-name cls-log-agent]
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NODE_START_RE = re.compile(
    r"^={10,}\s*\n\s*Node:\s*(\S+)\s*\n\s*={10,}", re.MULTILINE
)
TOOL_CALL_RE = re.compile(
    r"^\s*\[Tool Call\]:\s*(\w+)\(\)\s*(\{.*)", re.DOTALL
)
DATA_WRAP_RE = re.compile(r"<data[^>]*>(.*?)</data>", re.DOTALL)
TOOL_RESPONSE_LINE_RE = re.compile(r"^\[Tool\s+\S+\]:\s*(.*)", re.DOTALL)

# Nodes to skip entirely
SKIP_NODES = {"condense", "agent_tool_call_check", "todo_list_update"}

# Trailing separator line (─ characters)
SEP_LINE_RE = re.compile(r"^[─\-]{10,}\s*$")


def strip_data_wrapper(text: str) -> str:
    """Remove <data type="json">...</data> wrapper if present."""
    m = DATA_WRAP_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def split_into_nodes(raw: str):
    """
    Split raw stdout into a list of (node_name, node_body) tuples,
    preserving original order.
    """
    matches = list(NODE_START_RE.finditer(raw))
    nodes = []
    for i, m in enumerate(matches):
        node_name = m.group(1).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[body_start:body_end]
        # Strip trailing separator lines
        lines = body.splitlines()
        while lines and SEP_LINE_RE.match(lines[-1]):
            lines.pop()
        body = "\n".join(lines).strip()
        nodes.append((node_name, body))
    return nodes


def parse_tool_call(body: str):
    """
    Try to parse a tool call from the body of a Node: agent block.
    Returns (name, args_dict) or None if not a tool call.
    """
    # Collect the full tool call text (may span multiple lines)
    m = TOOL_CALL_RE.match(body.strip())
    if not m:
        return None
    func_name = m.group(1)
    json_fragment = m.group(2)
    # The JSON may be spread across lines; attempt to parse as-is
    try:
        args = json.loads(json_fragment)
    except json.JSONDecodeError:
        # Try accumulating lines until we get valid JSON
        args = json_fragment  # fallback: keep raw string
    return func_name, args


def build_conversations(nodes, system_prompt: str, human_query: str):
    """
    Convert parsed nodes into a ShareGPT conversations list.
    """
    convs = []

    # Always start with system + human
    if system_prompt:
        convs.append({"from": "system", "value": system_prompt})
    if human_query:
        convs.append({"from": "human", "value": human_query})

    pending_tool_name = None  # track most-recent tool call name for response label

    for node_name, body in nodes:
        if node_name in SKIP_NODES:
            continue

        if node_name == "agent":
            tc = parse_tool_call(body)
            if tc:
                func_name, args = tc
                pending_tool_name = func_name
                tool_call_value = json.dumps(
                    {"name": func_name, "arguments": args if isinstance(args, dict) else {"raw": args}},
                    ensure_ascii=False,
                )
                convs.append({"from": "tool_call", "value": tool_call_value})
            else:
                # Pure AI text response
                if body:
                    convs.append({"from": "gpt", "value": body})

        elif node_name == "tools":
            raw_response = strip_data_wrapper(body)
            # Optionally include tool name as context
            label = f"[{pending_tool_name}]: " if pending_tool_name else ""
            convs.append({"from": "tool_response", "value": label + raw_response})
            pending_tool_name = None

        elif node_name == "tool_responses_summary":
            if body:
                convs.append({"from": "gpt", "value": body, "role": "summary"})

        # Any other unrecognised node: skip silently

    return convs


def read_query(query_path: str) -> str:
    if query_path and os.path.isfile(query_path):
        with open(query_path, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def read_system_prompt(config_path: str) -> str:
    """Extract custom_system_prompt from config_snapshot.yaml (best-effort)."""
    if not config_path or not os.path.isfile(config_path):
        return ""
    try:
        import yaml  # type: ignore
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        prompt = (
            cfg.get("prompts", {}).get("custom_system_prompt", "")
            or ""
        )
        return prompt.strip()
    except Exception:
        pass
    # Fallback: simple line-based extraction
    with open(config_path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(
        r"custom_system_prompt:\s*\|\s*\n((?:(?:    |\t)[^\n]*\n?)*)",
        content,
    )
    if m:
        lines = m.group(1).splitlines()
        dedented = "\n".join(
            re.sub(r"^    ", "", line) for line in lines
        )
        return dedented.strip()
    return ""


def extract_timestamp_from_log(raw: str) -> str:
    """Try to extract an ISO-8601-like timestamp from the log preamble."""
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", raw)
    if m:
        return m.group(1)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def compute_format_hash(raw: str) -> str:
    """Compute a short hash representing the structural format of the log."""
    # Use the first 2000 chars for format fingerprinting
    sample = raw[:2000]
    return hashlib.md5(sample.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def convert(
    input_path: str,
    output_path: str,
    query_path: str = "",
    config_path: str = "",
    agent_name: str = "cls-log-agent",
):
    if not os.path.isfile(input_path):
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        raw = f.read()

    if not raw.strip():
        print("ERROR: execution_log.txt is empty", file=sys.stderr)
        sys.exit(1)

    nodes = split_into_nodes(raw)
    if not nodes:
        print(
            "WARNING: no nodes found in log — writing partial output",
            file=sys.stderr,
        )

    system_prompt = read_system_prompt(config_path)
    human_query = read_query(query_path)
    timestamp = extract_timestamp_from_log(raw)

    # Determine config_file basename
    config_file = os.path.basename(config_path) if config_path else ""

    conversations = build_conversations(nodes, system_prompt, human_query)

    parse_quality = "full" if nodes else "partial"

    result = {
        "conversations": conversations,
        "metadata": {
            "agent_name": agent_name,
            "platform": "observable_platform_agent",
            "timestamp": timestamp,
            "config_file": config_file,
            "query": human_query,
            "parse_quality": parse_quality,
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Converted {len(nodes)} nodes -> {len(conversations)} conversation turns")
    print(f"Output written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert platform execution_log.txt to ShareGPT JSON"
    )
    parser.add_argument("--input", required=True, help="Path to execution_log.txt")
    parser.add_argument("--output", required=True, help="Path to output run_log.json")
    parser.add_argument("--query", default="", help="Path to query.txt")
    parser.add_argument("--config", default="", help="Path to config_snapshot.yaml")
    parser.add_argument("--agent-name", default="cls-log-agent", help="Agent name")
    args = parser.parse_args()

    convert(
        input_path=args.input,
        output_path=args.output,
        query_path=args.query,
        config_path=args.config,
        agent_name=args.agent_name,
    )


if __name__ == "__main__":
    main()
