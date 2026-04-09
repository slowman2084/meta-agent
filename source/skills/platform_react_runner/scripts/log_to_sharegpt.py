#!/usr/bin/env python3
"""
log_to_sharegpt.py -- Platform execution log to ShareGPT JSON converter.

Adapted log format characteristics (platform_react_runner stdout):
  - Each node is framed by a pair of '=' lines (60 chars each):
        ============================================================
          Node: agent
        ============================================================
        <body lines>
        ============================================================   <- opens next node  OR
        ------------------------------------------------------------   <- very last end-of-section marker

  - Because consecutive nodes share a separator line (the closing '===' of one
    node is the opening '===' of the next), the state machine treats every '==='
    line seen while IN_BODY as the start of the next node header.

  - There is a single '─' (U+2500, 60 chars) line at the very end of the log,
    after the last node body, used as a final section terminator.

  - Agent output prefixes inside the 'agent' node:
      "  [Tool Call]: ToolName(){...args...}"   -> tool_call turn
      Plain text (no prefix)                   -> gpt turn

  - Tool output format: raw content, possibly wrapped in <data type="json">...</data>

  - Nodes to record:
      agent                  -> gpt (plain text) or tool_call
      tools                  -> tool_response
      tool_responses_summary -> gpt  (with role=summary metadata)

  - Nodes to skip: condense, agent_tool_call_check, todo_list_update

Usage:
    python3 log_to_sharegpt.py --input execution_log.txt --output run_log.json \\
        [--query query.txt] [--config config_snapshot.yaml] [--agent-name NAME]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

# A line composed entirely of '=' characters (60+) -- node header separator
NODE_HDR_RE = re.compile(r"^={10,}\s*$")
# The "  Node: <name>" label line
NODE_LABEL_RE = re.compile(r"^\s{2}Node:\s+(\S+)\s*$")
# A line composed entirely of '─' (U+2500) or '-' chars -- final section separator
FINAL_SEP_RE = re.compile(r"^[─\-]{10,}\s*$")
# Tool-call line inside an agent node.
# Uses \s* so the pattern matches even when the first body line has had its
# leading whitespace stripped (e.g. after a strip() on the joined body).
TOOL_CALL_RE = re.compile(r"^\s*\[Tool Call\]:\s*(.+)$")
# <data ...>...</data> wrapper
DATA_WRAP_RE = re.compile(r"<data[^>]*>(.*)</data>", re.DOTALL)

SKIP_NODES = {"condense", "agent_tool_call_check", "todo_list_update"}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _strip_data_wrapper(text: str) -> str:
    """Remove <data type=\"json\">...</data> wrapper if present."""
    m = DATA_WRAP_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _parse_tool_call_value(raw: str) -> str:
    """
    Convert a raw tool-call string such as:
        SearchLog(){"From": 123, "To": 456}
    or:
        ConvertTimestampToTimeString()
    into a JSON string:
        {"name": "SearchLog", "arguments": {"From": 123, "To": 456}}
    """
    m = re.match(r"^(\w+)\([^)]*\)\s*(\{.*\})?$", raw, re.DOTALL)
    if m:
        name = m.group(1)
        args_str = (m.group(2) or "{}").strip()
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {"_raw": args_str}
        return json.dumps({"name": name, "arguments": args}, ensure_ascii=False)

    # Fallback: treat the whole string as the tool name with empty args.
    name = raw.split("(")[0].strip() if "(" in raw else raw.strip()
    return json.dumps({"name": name, "arguments": {}}, ensure_ascii=False)


def _split_agent_lines(body_lines: list) -> list:
    """
    Split raw agent-node body lines into a list of (from_type, value) tuples.
    Lines matching TOOL_CALL_RE become 'tool_call' entries.
    Contiguous non-tool-call lines become 'gpt' entries.

    Accepts a list of raw lines (not a pre-joined/stripped string) so that
    the original leading whitespace of each line is preserved for matching.
    """
    segments = []
    gpt_buf = []

    for line in body_lines:
        tc_m = TOOL_CALL_RE.match(line)
        if tc_m:
            if gpt_buf:
                text = "\n".join(gpt_buf).strip()
                if text:
                    segments.append(("gpt", text))
                gpt_buf = []
            segments.append(("tool_call", _parse_tool_call_value(tc_m.group(1).strip())))
        else:
            gpt_buf.append(line)

    if gpt_buf:
        text = "\n".join(gpt_buf).strip()
        if text:
            segments.append(("gpt", text))

    return segments


def _flush_node(node_name: str, body_lines: list, turns: list) -> None:
    """Convert a completed node body into conversation turns."""
    if node_name is None or node_name in SKIP_NODES:
        return

    # Quick emptiness check on joined body.
    body = "\n".join(body_lines).strip()
    if not body:
        return

    if node_name == "agent":
        # Pass the raw line list so leading spaces are intact for TOOL_CALL_RE.
        for seg_type, seg_val in _split_agent_lines(body_lines):
            turns.append({"from": seg_type, "value": seg_val, "_meta": {}})

    elif node_name == "tools":
        turns.append({"from": "tool_response",
                       "value": _strip_data_wrapper(body),
                       "_meta": {}})

    elif node_name == "tool_responses_summary":
        turns.append({"from": "gpt", "value": body, "_meta": {"role": "summary"}})


# ---------------------------------------------------------------------------
# Main log parser
# ---------------------------------------------------------------------------

def parse_log(log_text: str) -> list:
    """
    Parse the platform runner stdout and return a list of conversation turns.

    State machine transitions:
      OUTSIDE      -- ignoring preamble lines; first '===' -> HDR_TOP
      HDR_TOP      -- just saw '==='; next meaningful line should be 'Node: name'
      HDR_BOT      -- saw 'Node: name'; next '===' -> IN_BODY
      IN_BODY      -- collecting body lines:
                       * another '===' -> flush current, go to HDR_TOP
                       * '───' (final sep) -> flush current, go to OUTSIDE
    """
    lines = log_text.splitlines()
    turns: list = []

    state = "OUTSIDE"
    current_node = None
    current_lines: list = []

    for line in lines:
        is_hdr = bool(NODE_HDR_RE.match(line))
        is_final_sep = bool(FINAL_SEP_RE.match(line))
        label_m = NODE_LABEL_RE.match(line) if not is_hdr else None

        if state == "OUTSIDE":
            if is_hdr:
                state = "HDR_TOP"

        elif state == "HDR_TOP":
            if label_m:
                current_node = label_m.group(1)
                state = "HDR_BOT"
            elif is_hdr:
                pass  # two consecutive '===' lines -- stay in HDR_TOP
            else:
                state = "OUTSIDE"

        elif state == "HDR_BOT":
            if is_hdr:
                # closing '===' of the header pair; body starts now
                current_lines = []
                state = "IN_BODY"
            else:
                state = "OUTSIDE"

        elif state == "IN_BODY":
            if is_hdr:
                # The closing '===' of this node is the opening '===' of the next.
                _flush_node(current_node, current_lines, turns)
                current_node = None
                current_lines = []
                state = "HDR_TOP"
            elif is_final_sep:
                # Final '───' separator ends the last node.
                _flush_node(current_node, current_lines, turns)
                current_node = None
                current_lines = []
                state = "OUTSIDE"
            else:
                current_lines.append(line)

    # Flush any remaining in-progress node (no trailing separator).
    if state == "IN_BODY" and current_node:
        _flush_node(current_node, current_lines, turns)

    return turns


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def load_query(query_file: str) -> str:
    if query_file and os.path.isfile(query_file):
        with open(query_file, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def load_config_meta(config_file: str) -> dict:
    """Extract platform identifier and config filename from config_snapshot.yaml."""
    meta = {"platform": "", "config_file": ""}
    if not config_file or not os.path.isfile(config_file):
        return meta

    meta["config_file"] = os.path.basename(config_file)

    try:
        with open(config_file, encoding="utf-8") as f:
            content = f.read()
        # Use graph.name as the platform identifier.
        m = re.search(r"^\s*name:\s*[\"']?([^\"'\n]+)[\"']?", content, re.MULTILINE)
        if m:
            meta["platform"] = m.group(1).strip()
    except Exception:
        pass
    return meta


def extract_timestamp_from_log(log_text: str) -> str:
    """Extract the first ISO-ish datetime from the log, or use now."""
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log_text)
    if m:
        return m.group(1)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Top-level conversion function
# ---------------------------------------------------------------------------

def convert(
    input_log: str,
    output_json: str,
    query_file: str = None,
    config_file: str = None,
    agent_name: str = "cls-log-agent",
    system_prompt: str = None,
    human_query: str = None,
) -> dict:
    if not os.path.isfile(input_log):
        print(f"ERROR: input file not found: {input_log}", file=sys.stderr)
        sys.exit(1)

    with open(input_log, encoding="utf-8") as f:
        log_text = f.read()

    if not log_text.strip():
        print(f"ERROR: input file is empty: {input_log}", file=sys.stderr)
        sys.exit(1)

    turns = parse_log(log_text)

    conversations = []

    if system_prompt:
        conversations.append({"from": "system", "value": system_prompt})

    query = human_query or load_query(query_file)
    if query:
        conversations.append({"from": "human", "value": query})

    for turn in turns:
        entry = {"from": turn["from"], "value": turn["value"]}
        if turn.get("_meta", {}).get("role") == "summary":
            entry["role"] = "summary"
        conversations.append(entry)

    config_meta = load_config_meta(config_file)
    timestamp = extract_timestamp_from_log(log_text)

    metadata = {
        "agent_name": agent_name,
        "platform": config_meta.get("platform", ""),
        "timestamp": timestamp,
        "config_file": config_meta.get("config_file", ""),
        "query": query,
    }

    result = {"conversations": conversations, "metadata": metadata}

    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(conversations)} conversation entries to: {output_json}")
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert platform execution log to ShareGPT JSON."
    )
    parser.add_argument("--input", required=True, help="Path to execution_log.txt")
    parser.add_argument("--output", required=True, help="Path to output run_log.json")
    parser.add_argument("--query", default=None, help="Path to query.txt")
    parser.add_argument("--config", default=None, help="Path to config_snapshot.yaml")
    parser.add_argument("--agent-name", default="cls-log-agent",
                        help="Agent name written into metadata")
    args = parser.parse_args()

    convert(
        input_log=args.input,
        output_json=args.output,
        query_file=args.query,
        config_file=args.config,
        agent_name=args.agent_name,
    )


if __name__ == "__main__":
    main()
