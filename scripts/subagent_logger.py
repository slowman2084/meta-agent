#!/usr/bin/env python3
"""
SubagentStop Hook Logger

Triggered by Claude Code's SubagentStop hook when a Sub Agent completes.
Reads the agent's JSONL transcript from the hook payload, converts it to
ShareGPT JSON format, and writes it to the appropriate output directory
based on the current Agent Factory context.

Stdin format (from Claude Code hook):
  {
    "session_id": "...",
    "transcript_path": ".../.../session.jsonl",
    "agent_transcript_path": ".../.../subagents/agent-<id>.jsonl",
    "agent_id": "a...",
    "cwd": "/path/to/project",
    "hook_event_name": "SubagentStop",
    "stop_hook_active": false,
    ...
  }

Output directory logic (based on .agent_factory_context.json):
  - mode=evalooper, iteration=N  -> source/[agent]/tmp/evalooper/iter_[N]/run_[ts].json
  - mode=test_agent, session=S   -> source/[agent]/tmp/test_[S]/run_[ts].json
  - fallback                     -> source/[agent]/tmp/hook_logs/run_[ts].json
"""

import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime


# ---- Logging setup ----

def setup_debug_logger():
    log_path = Path.home() / ".claude" / "subagent_hook_debug.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("subagent_logger")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
    return logger


# ---- JSONL transcript parser (ShareGPT converter) ----

def parse_jsonl_transcript(input_path: str, agent_name: str = "unknown") -> dict:
    """Convert a Claude Code JSONL transcript to ShareGPT format."""
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

    # Pass 1: build tool_use id -> tool name map
    tool_use_map = {}
    for rec in records:
        if rec.get("type") == "assistant":
            msg = rec.get("message", {})
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_use_map[block["id"]] = block.get("name", "unknown_tool")

    # Pass 2: build conversation turns in record order, deduplicating by block key
    seen_blocks = set()
    first_timestamp = ""

    for rec in records:
        rec_type = rec.get("type")
        ts = rec.get("timestamp", "")
        if ts and not first_timestamp:
            first_timestamp = ts

        if rec_type == "progress":
            continue

        if rec_type == "user":
            msg = rec.get("message", {})
            content = msg.get("content", "")

            # Plain text user message (original human query)
            if isinstance(content, str) and content.strip():
                if not metadata["query"]:
                    metadata["query"] = content.strip()
                conversations.append({"from": "human", "value": content.strip()})

            # List content -> tool_result responses
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id", "")
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            parts = [c.get("text", "") for c in result_content if c.get("type") == "text"]
                            result_text = "\n".join(parts)
                        elif isinstance(result_content, str):
                            result_text = result_content
                        else:
                            result_text = str(result_content)

                        block_key = ("tool_result", tool_use_id)
                        if block_key not in seen_blocks:
                            seen_blocks.add(block_key)
                            conversations.append({"from": "tool_response", "value": result_text})

        elif rec_type == "assistant":
            msg = rec.get("message", {})
            msg_id = msg.get("id", "")
            content_blocks = msg.get("content", [])

            if not metadata["session_id"]:
                metadata["session_id"] = rec.get("sessionId", "")
                metadata["agent_id"] = rec.get("agentId", "")

            for b_idx, block in enumerate(content_blocks):
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")

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
                        conversations.append({"from": "gpt", "value": text})
                elif block_type == "tool_use":
                    tool_name = block.get("name", "unknown_tool")
                    tool_input = block.get("input", {})
                    conversations.append({
                        "from": "tool_call",
                        "value": json.dumps({"name": tool_name, "arguments": tool_input}, ensure_ascii=False),
                    })

    metadata["timestamp"] = first_timestamp

    return {"conversations": conversations, "metadata": metadata}


# ---- Context reader ----

def read_context(project_root):
    """Read .agent_factory_context.json if it exists."""
    context_file = Path(project_root) / ".agent_factory_context.json"
    if context_file.exists():
        try:
            return json.loads(context_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


# ---- Output path resolver ----

def resolve_output_dir(project_root, context):
    """Determine where to write the run log based on context."""
    project_root = Path(project_root)
    agent_name = context.get("agent_name", "")
    mode = context.get("mode", "")

    if not agent_name:
        return project_root / "tmp" / "hook_logs"

    agent_dir = project_root / "source" / agent_name / "tmp"

    if mode == "evalooper":
        iteration = context.get("iteration", 1)
        return agent_dir / "evalooper" / f"iter_{iteration}"
    elif mode == "test_agent":
        session_id = context.get("session_id", "")
        if session_id:
            return agent_dir / f"test_{session_id}"
        else:
            return agent_dir / "hook_logs"
    else:
        return agent_dir / "hook_logs"


# ---- Main ----

def main():
    logger = setup_debug_logger()
    logger.info("=== SubagentStop Hook Started ===")

    # Read stdin payload
    raw_input = sys.stdin.buffer.read()
    payload_str = raw_input.decode("utf-8", errors="replace").strip()

    logger.info(f"Received payload: {payload_str[:500]}")

    # Parse payload
    try:
        payload = json.loads(payload_str) if payload_str else {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse payload JSON: {e}")
        payload = {}

    # Determine project root from cwd or CLAUDE_PROJECT_DIR
    cwd = payload.get("cwd", "") or os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()
    project_root = Path(cwd)

    # Read agent factory context
    context = read_context(project_root)
    agent_name = context.get("agent_name", "unknown")

    # Get transcript path
    # Prefer agent_transcript_path (Sub Agent's own JSONL), fall back to transcript_path
    transcript_path = (
        payload.get("agent_transcript_path")
        or payload.get("transcript_path")
        or ""
    )

    logger.info(
        f"Initial: agent_name={agent_name}, transcript_path={transcript_path}, cwd={cwd}"
    )

    # Verify agent source directory exists
    agent_source_dir = project_root / "source" / agent_name
    logger.info(f"Checking agent_dir: {agent_source_dir}, exists={agent_source_dir.exists()}")

    # Determine output directory
    output_dir = resolve_output_dir(project_root, context)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"run_{ts}.json"

    # Convert transcript
    conversations = []
    metadata = {"agent_name": agent_name, "platform": "claude-code-jsonl", "timestamp": "", "query": ""}

    if transcript_path and Path(transcript_path).exists():
        try:
            result = parse_jsonl_transcript(transcript_path, agent_name=agent_name)
            conversations = result.get("conversations", [])
            metadata = result.get("metadata", metadata)
            logger.info(f"Extracted {len(conversations)} conversation turns from transcript")
        except Exception as e:
            logger.error(f"Failed to parse transcript: {e}")
            conversations = []
    else:
        logger.warning(f"Transcript not found or empty: {transcript_path}")

    # Fallback: create minimal record if no conversations extracted
    if not conversations:
        logger.info("No conversations extracted, creating fallback record")
        metadata["note"] = "no_conversations_extracted"

    # Enrich metadata with hook payload info
    metadata["hook_session_id"] = payload.get("session_id", "")
    metadata["hook_agent_id"] = payload.get("agent_id", "")
    metadata["hook_transcript_path"] = transcript_path
    metadata["context_mode"] = context.get("mode", "")
    metadata["context_iteration"] = context.get("iteration", "")

    # Write output
    output_data = {"conversations": conversations, "metadata": metadata}
    try:
        output_file.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Successfully wrote log to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to write log: {e}")
        sys.exit(1)

    logger.info("=== SubagentStop Hook Completed ===")


if __name__ == "__main__":
    main()
