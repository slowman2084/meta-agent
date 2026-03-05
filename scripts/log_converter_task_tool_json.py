#!/usr/bin/env python3
"""
Task Tool JSON Result -> ShareGPT Format Converter

Adapted format: Task tool returned JSON transcript files
Format characteristics:
- Single JSON object (not JSONL)
- Contains "result" object with:
  - "finalResult": The final output text from the agent
  - "toolInfo": Array of tool call records with "name", "info", "executeStatus"
  - "toolCallBrief": Summary of execution (tool count, cost, etc.)
- Top-level "status" and "success" fields indicate execution status

Mapping rules:
- toolInfo records -> tool_call + tool_response pairs
- finalResult -> gpt turn (final answer)
- Query is extracted from context or left empty

Usage:
    python3 log_converter_task_tool_json.py --input <input.json> --output <output.json> --agent-name <name> [--query <query>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_task_tool_json(input_path: str, agent_name: str = "unknown", query: str = "") -> dict:
    """Parse Task tool JSON result file to ShareGPT format."""
    
    content = Path(input_path).read_text(encoding="utf-8")
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    conversations = []
    metadata = {
        "agent_name": agent_name,
        "platform": "task-tool-json",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_file": "",
        "query": query,
        "parse_quality": "full",
    }
    
    # Extract status info
    status = data.get("status", "unknown")
    success = data.get("success", False)
    result = data.get("result", {})
    
    # Extract tool call brief for metadata
    tool_call_brief = result.get("toolCallBrief", "")
    metadata["tool_call_brief"] = tool_call_brief
    
    # Add human query if provided
    if query:
        conversations.append({
            "from": "human",
            "value": query
        })
    
    # Process tool info
    tool_info_list = result.get("toolInfo", [])
    
    for tool_info in tool_info_list:
        tool_name = tool_info.get("name", "unknown_tool")
        tool_response = tool_info.get("info", "")
        execute_status = tool_info.get("executeStatus", "unknown")
        
        # Add tool_call turn
        conversations.append({
            "from": "tool_call",
            "value": json.dumps({
                "name": tool_name,
                "arguments": {}
            }, ensure_ascii=False)
        })
        
        # Add tool_response turn
        # Format response with status indicator
        response_text = tool_response
        if execute_status and execute_status != "unknown":
            response_text = f"[Status: {execute_status}] {tool_response}"
        
        conversations.append({
            "from": "tool_response",
            "value": response_text
        })
    
    # Add final result as gpt turn
    final_result = result.get("finalResult", "")
    if final_result:
        conversations.append({
            "from": "gpt",
            "value": final_result
        })
    
    # Check for errors
    error_message = result.get("errorMessage", "") or data.get("errorMessage", "")
    if error_message:
        metadata["error_message"] = error_message
        metadata["parse_quality"] = "partial"
    
    return {
        "conversations": conversations,
        "metadata": metadata
    }


def main():
    parser = argparse.ArgumentParser(description="Convert Task Tool JSON result to ShareGPT format")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Name of the agent being tested")
    parser.add_argument("--query", default="", help="Original query/question (optional)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = parse_task_tool_json(args.input, agent_name=args.agent_name, query=args.query)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
