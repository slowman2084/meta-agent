#!/usr/bin/env python3
"""
MCP Transcript JSON -> ShareGPT Format Converter

Adapted format: MCP tool call transcript files (JSON array)
Format characteristics:
- Single JSON array of MCP tool call records
- Each record has:
  - "name": Tool name (e.g., "MCP Get Tool Description", "MCP Call Tool")
  - "info": Tool execution info/result
  - "toolCallId": Unique identifier for the tool call
  - "executeStatus": Execution status (e.g., "completed", "failed")

Mapping rules:
- MCP Get Tool Description -> tool_call (for getting tool metadata)
- MCP Call Tool -> tool_call + tool_response pair
- Final output from actual_output.txt -> gpt turn
- Query extracted from external source (testcases.yaml or provided via argument)

Usage:
    python3 log_converter_mcp_transcript.py --input <input.json> --output <output.json> --agent-name <name> [--query <query>] [--actual-output <actual_output.txt>]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_mcp_transcript(
    input_path: str,
    agent_name: str = "unknown",
    query: str = "",
    actual_output_path: str = ""
) -> dict:
    """Parse MCP transcript JSON file to ShareGPT format."""
    
    content = Path(input_path).read_text(encoding="utf-8")
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not isinstance(data, list):
        print("ERROR: Input JSON is not a list", file=sys.stderr)
        sys.exit(1)
    
    conversations = []
    metadata = {
        "agent_name": agent_name,
        "platform": "mcp-transcript",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_file": "",
        "query": query,
        "parse_quality": "full",
    }
    
    # Add human query if provided
    if query:
        conversations.append({
            "from": "human",
            "value": query
        })
    
    # Process MCP tool calls
    for record in data:
        name = record.get("name", "unknown_tool")
        info = record.get("info", "")
        tool_call_id = record.get("toolCallId", "")
        execute_status = record.get("executeStatus", "unknown")
        
        # Extract tool name from info field
        # Examples:
        # - "Retrieved servers(s) from [["cls-mcp-server", "ConvertTimestampToTimeString"]] completed!"
        # - "MCP "cls-mcp-server" tool ConvertTimestampToTimeString completed!"
        
        tool_name = ""
        tool_args = {}
        
        if name == "MCP Get Tool Description":
            # Parse: Retrieved servers(s) from [["server", "tool"]] completed!
            match = re.search(r'\[\["([^"]+)",\s*"([^"]+)"\]\]', info)
            if match:
                server_name = match.group(1)
                tool_name_from_info = match.group(2)
                tool_name = f"{server_name}.{tool_name_from_info}"
            else:
                tool_name = "MCP Get Tool Description"
            
            # Add tool_call
            conversations.append({
                "from": "tool_call",
                "value": json.dumps({
                    "name": name,
                    "arguments": {
                        "tool": tool_name
                    },
                    "toolCallId": tool_call_id
                }, ensure_ascii=False)
            })
            
            # Add tool_response
            response_text = f"[Status: {execute_status}] {info}"
            conversations.append({
                "from": "tool_response",
                "value": response_text
            })
            
        elif name == "MCP Call Tool":
            # Parse: MCP "cls-mcp-server" tool ConvertTimestampToTimeString completed!
            match = re.search(r'MCP "([^"]+)" tool ([^\s]+)', info)
            if match:
                server_name = match.group(1)
                tool_name_from_info = match.group(2)
                tool_name = f"{server_name}.{tool_name_from_info}"
            else:
                tool_name = name
            
            # Add tool_call
            conversations.append({
                "from": "tool_call",
                "value": json.dumps({
                    "name": tool_name,
                    "arguments": {},
                    "toolCallId": tool_call_id
                }, ensure_ascii=False)
            })
            
            # Add tool_response
            response_text = f"[Status: {execute_status}] {info}"
            conversations.append({
                "from": "tool_response",
                "value": response_text
            })
        
        else:
            # Generic handling for other tool types
            conversations.append({
                "from": "tool_call",
                "value": json.dumps({
                    "name": name,
                    "arguments": {},
                    "toolCallId": tool_call_id
                }, ensure_ascii=False)
            })
            
            response_text = f"[Status: {execute_status}] {info}"
            conversations.append({
                "from": "tool_response",
                "value": response_text
            })
    
    # Add final result as gpt turn if actual_output_path is provided
    if actual_output_path and Path(actual_output_path).exists():
        final_result = Path(actual_output_path).read_text(encoding="utf-8")
        if final_result.strip():
            conversations.append({
                "from": "gpt",
                "value": final_result
            })
    
    return {
        "conversations": conversations,
        "metadata": metadata
    }


def main():
    parser = argparse.ArgumentParser(description="Convert MCP transcript JSON to ShareGPT format")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output ShareGPT JSON file")
    parser.add_argument("--agent-name", default="unknown", help="Name of the agent being tested")
    parser.add_argument("--query", default="", help="Original query/question")
    parser.add_argument("--actual-output", default="", help="Path to actual output file (final agent response)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = parse_mcp_transcript(
        args.input,
        agent_name=args.agent_name,
        query=args.query,
        actual_output_path=args.actual_output
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(result['conversations'])} conversation turns to {args.output}")


if __name__ == "__main__":
    main()
