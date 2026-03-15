#!/usr/bin/env python3
"""
SubAgent ShareGPT 格式导出器

用途：
  在 Sub Agent 执行前后分别调用，自动对比快照，提取新增的 Sub Agent 对话，
  并导出为标准 ShareGPT 格式的 JSON 文件。

使用流程：
  1. 执行前 — 记录快照：
     ./venv/bin/python scripts/subagent_sharegpt_exporter.py snapshot

  2. （执行你的 Sub Agent 任务……）

  3. 执行后 — 导出新增记录：
     ./venv/bin/python scripts/subagent_sharegpt_exporter.py export

     或分拆导出（test_agent 流程用）：
     ./venv/bin/python scripts/subagent_sharegpt_exporter.py export-split -d output_dir/

     可选参数：
       --output  指定输出文件路径（默认 logs/sharegpt_exports/{timestamp}_subagents.json）
       --pretty  美化 JSON 输出
       --raw     同时保存原始 finalResult（方便调试）

依赖：无（纯 Python 标准库）
"""

import sys
import json
import os
import re
import glob
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# 启用实时输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# ======================================================================
# 默认配置
# ======================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")

DEFAULT_CONFIG = {
    # CodeBuddy 数据根目录（macOS）
    "CODEBUDDY_DATA_ROOT": os.path.expanduser(
        "~/Library/Application Support/CodeBuddyExtension/Data/"
    ),
    # 快照文件存储位置
    "SNAPSHOT_FILE": os.path.join(PROJECT_ROOT, "logs", ".subagent_snapshot.json"),
    # 默认导出目录
    "EXPORT_DIR": os.path.join(PROJECT_ROOT, "logs", "sharegpt_exports"),
}


# ======================================================================
# 1. Transcript 发现与读取
# ======================================================================

def find_latest_sessions(data_root: str, limit: int = 10) -> List[str]:
    """
    自动发现最近的会话 index.json 文件。

    Returns:
        按修改时间降序排列的 index.json 路径列表
    """
    pattern = os.path.join(data_root, "**/history/**/index.json")
    files = glob.glob(pattern, recursive=True)

    files_with_mtime = []
    for f in files:
        if os.path.isfile(f):
            try:
                files_with_mtime.append((f, os.path.getmtime(f)))
            except OSError:
                continue

    files_with_mtime.sort(key=lambda x: x[1], reverse=True)
    return [f for f, _ in files_with_mtime[:limit]]


def read_index(transcript_path: str) -> dict:
    """读取 index.json 并返回完整内容"""
    if not os.path.exists(transcript_path):
        return {}
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def read_message(messages_dir: str, msg_id: str) -> dict:
    """读取单条消息 JSON 文件"""
    msg_file = os.path.join(messages_dir, f"{msg_id}.json")
    if not os.path.exists(msg_file):
        return {}
    try:
        with open(msg_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        message_str = data.get("message", "")
        return json.loads(message_str) if message_str else {}
    except (json.JSONDecodeError, IOError, TypeError):
        return {}


# ======================================================================
# 2. 快照功能
# ======================================================================

def take_snapshot(data_root: str, snapshot_file: str, session_limit: int = 10):
    """
    记录当前所有会话的消息数量快照。

    快照内容：
    {
        "timestamp": "...",
        "sessions": {
            "/path/to/index.json": {
                "message_count": 42,
                "message_ids": ["id1", "id2", ...]
            }
        }
    }
    """
    print("1️⃣  正在扫描 CodeBuddy 会话目录...", flush=True)

    sessions = find_latest_sessions(data_root, limit=session_limit)
    print(f"   发现 {len(sessions)} 个会话", flush=True)

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "data_root": data_root,
        "sessions": {},
    }

    for i, session_path in enumerate(sessions, 1):
        index = read_index(session_path)
        messages = index.get("messages", [])
        msg_ids = [m.get("id", "") for m in messages]

        snapshot["sessions"][session_path] = {
            "message_count": len(messages),
            "message_ids": msg_ids,
        }

        print(f"   [{i}/{len(sessions)}] {os.path.basename(os.path.dirname(session_path))}: "
              f"{len(messages)} 条消息", flush=True)

    # 保存快照
    os.makedirs(os.path.dirname(snapshot_file), exist_ok=True)
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    file_size_kb = os.path.getsize(snapshot_file) / 1024
    print(f"\n2️⃣  快照已保存:", flush=True)
    print(f"   文件: {snapshot_file}", flush=True)
    print(f"   大小: {file_size_kb:.2f} KB", flush=True)
    print(f"   会话数: {len(snapshot['sessions'])}", flush=True)
    print(f"   总消息: {sum(s['message_count'] for s in snapshot['sessions'].values())}", flush=True)

    return snapshot


def load_snapshot(snapshot_file: str) -> dict:
    """加载之前保存的快照"""
    if not os.path.exists(snapshot_file):
        return {}
    try:
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


# ======================================================================
# 3. 差异对比：找出新增消息
# ======================================================================

def find_new_messages(
    data_root: str,
    old_snapshot: dict,
    session_limit: int = 10
) -> List[Tuple[str, str, dict]]:
    """
    对比快照，找出每个会话中新增的消息。

    Returns:
        [(transcript_path, msg_id, msg_meta), ...] 的列表
    """
    new_messages = []

    # 重新扫描当前会话
    current_sessions = find_latest_sessions(data_root, limit=session_limit)
    old_sessions = old_snapshot.get("sessions", {})

    for session_path in current_sessions:
        index = read_index(session_path)
        current_msgs = index.get("messages", [])

        # 获取旧快照中该会话的消息 ID 集合
        old_info = old_sessions.get(session_path, {})
        old_ids = set(old_info.get("message_ids", []))

        # 找出新增的消息
        for msg_meta in current_msgs:
            msg_id = msg_meta.get("id", "")
            if msg_id and msg_id not in old_ids:
                new_messages.append((session_path, msg_id, msg_meta))

    return new_messages


# ======================================================================
# 4. Sub Agent 记录提取
# ======================================================================

def extract_subagent_from_new_messages(
    new_messages: List[Tuple[str, str, dict]]
) -> List[Dict[str, Any]]:
    """
    从新增消息中提取 Sub Agent 的完整记录。

    策略：
      1. 先收集所有新增的 assistant 消息中的 task tool-call（建立 toolCallId → subagent_info 映射）
      2. 再收集所有新增的 tool 消息中 toolName=task 的返回（通过 toolCallId 关联）
    """
    # 分组：按 session 聚合
    session_msgs = {}  # session_path → [msg_id, msg_meta]
    for session_path, msg_id, msg_meta in new_messages:
        if session_path not in session_msgs:
            session_msgs[session_path] = []
        session_msgs[session_path].append((msg_id, msg_meta))

    all_records = []

    for session_path, msgs in session_msgs.items():
        messages_dir = os.path.join(os.path.dirname(session_path), "messages")

        # 第一遍：收集 assistant 消息中的 task tool-call
        # toolCallId → {subagent_name, description, prompt}
        tool_call_map = {}
        # 第二遍要处理的 tool 消息
        tool_msgs = []

        for msg_id, msg_meta in msgs:
            role = msg_meta.get("role", "")
            content = read_message(messages_dir, msg_id)
            if not content:
                continue

            if role == "assistant":
                for block in content.get("content", []):
                    if block.get("type") == "tool-call" and block.get("toolName") == "task":
                        tc_id = block.get("toolCallId", "")
                        args = block.get("args", {})
                        if tc_id:
                            tool_call_map[tc_id] = {
                                "subagent_name": args.get("subagent_name", "unknown"),
                                "description": args.get("description", ""),
                                "prompt": args.get("prompt", ""),
                            }

            elif role == "tool":
                tool_msgs.append((msg_id, content))

        # 第二遍：处理 tool 消息，提取 Sub Agent 结果
        for msg_id, content in tool_msgs:
            for item in content.get("content", []):
                if item.get("toolName") != "task":
                    continue

                tc_id = item.get("toolCallId", "")
                result = item.get("result", {})
                inner_result = result.get("result", result)
                final_result = inner_result.get("finalResult", "")
                usage = inner_result.get("usage", {})
                tool_brief = inner_result.get("toolCallBrief", "")

                # 从映射表查 subagent 信息
                agent_info = tool_call_map.get(tc_id, {})
                if not agent_info:
                    # 如果映射表找不到（可能 assistant 消息不在新增范围内），
                    # 回退到全量搜索 index.json
                    agent_info = _fallback_find_agent_info(session_path, messages_dir, tc_id)

                record = {
                    "msg_id": msg_id,
                    "tool_call_id": tc_id,
                    "session_path": session_path,
                    "subagent_name": agent_info.get("subagent_name", "unknown"),
                    "description": agent_info.get("description", ""),
                    "prompt": agent_info.get("prompt", ""),
                    "final_result": final_result,
                    "usage": usage,
                    "tool_call_brief": tool_brief,
                }
                all_records.append(record)

    return all_records


def _fallback_find_agent_info(session_path: str, messages_dir: str, tool_call_id: str) -> dict:
    """回退方法：从整个 index.json 中搜索 toolCallId 对应的 assistant 消息"""
    result = {"subagent_name": "unknown", "description": "", "prompt": ""}
    if not tool_call_id:
        return result

    index = read_index(session_path)
    for msg_meta in index.get("messages", []):
        if msg_meta.get("role") != "assistant":
            continue

        msg_id = msg_meta.get("id", "")
        content = read_message(messages_dir, msg_id)
        if not content:
            continue

        for block in content.get("content", []):
            if (block.get("type") == "tool-call"
                    and block.get("toolCallId") == tool_call_id):
                args = block.get("args", {})
                return {
                    "subagent_name": args.get("subagent_name", "unknown"),
                    "description": args.get("description", ""),
                    "prompt": args.get("prompt", ""),
                }

    return result


# ======================================================================
# 5. finalResult → ShareGPT 格式转换
# ======================================================================

def parse_final_result_to_sharegpt(
    final_result: str,
    subagent_name: str,
    prompt: str,
    description: str
) -> Dict[str, Any]:
    """
    将 Sub Agent 的 finalResult 解析为 ShareGPT 格式。

    ShareGPT 格式：
    {
      "conversations": [
        {"from": "system", "value": "..."},
        {"from": "human", "value": "..."},
        {"from": "gpt", "value": "..."},
        {"from": "tool_call", "value": "..."},
        {"from": "tool_response", "value": "..."},
        {"from": "gpt", "value": "..."},
        ...
      ]
    }

    解析策略：
      finalResult 是一段混合文本，包含 Sub Agent 的思考/输出。
      支持两种工具调用格式：

      格式A（JSON，标准 CodeBuddy 格式）：
        <tool_call>{"name":"...", "arguments":{...}}</tool_call>
        <tool_result>...</tool_result>

      格式B（XML，某些 Sub Agent 使用）：
        <tool_call>
        <tool_name>Bash</tool_name>
        <parameters><command>...</command></parameters>
        </tool_call>
        (无 tool_result，结果内嵌在后续文本中)

      我们将其拆分为交替的 gpt/tool_call/tool_response 片段。
    """
    conversations = []

    # system 消息：记录 SubAgent 元信息
    system_msg = f"SubAgent: {subagent_name}"
    if description:
        system_msg += f"\nDescription: {description}"
    conversations.append({"from": "system", "value": system_msg})

    # human 消息：用户给 SubAgent 的 prompt
    conversations.append({"from": "human", "value": prompt or "(no prompt)"})

    # 解析 finalResult — 使用统一的拆分策略
    # 先尝试格式A（带 tool_result 的标准格式）
    pattern_a = re.compile(
        r'(<tool_call>\s*)(.*?)(\s*</tool_call>\s*<tool_result>\s*)(.*?)(\s*</tool_result>)',
        re.DOTALL
    )

    # 格式B（只有 tool_call，无 tool_result）
    pattern_b = re.compile(
        r'<tool_call>\s*(.*?)\s*</tool_call>',
        re.DOTALL
    )

    # 先检查是否有格式A的匹配
    has_format_a = bool(pattern_a.search(final_result))

    if has_format_a:
        # 格式A：标准 JSON tool_call + tool_result 对
        last_end = 0
        for match in pattern_a.finditer(final_result):
            text_before = final_result[last_end:match.start()].strip()
            if text_before:
                conversations.append({"from": "gpt", "value": text_before})

            call_raw = match.group(2).strip()
            tool_call_value = call_raw
            tool_name = "unknown"
            try:
                call_data = json.loads(call_raw)
                tool_name = call_data.get("name", "unknown")
                tool_call_value = json.dumps(call_data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                tool_name = _extract_xml_tool_name(call_raw)

            conversations.append({
                "from": "tool_call",
                "value": tool_call_value,
                "tool_name": tool_name,
            })

            result_raw = match.group(4).strip()
            conversations.append({
                "from": "tool_response",
                "value": result_raw,
                "tool_name": tool_name,
            })

            last_end = match.end()

        text_after = final_result[last_end:].strip()
        if text_after:
            conversations.append({"from": "gpt", "value": text_after})

    else:
        # 格式B 或混合：按 <tool_call>...</tool_call> 拆分（无 tool_result）
        last_end = 0
        found_any = False
        for match in pattern_b.finditer(final_result):
            found_any = True
            text_before = final_result[last_end:match.start()].strip()
            if text_before:
                conversations.append({"from": "gpt", "value": text_before})

            call_raw = match.group(1).strip()
            tool_call_value = call_raw
            tool_name = "unknown"

            # 尝试 JSON 解析
            try:
                call_data = json.loads(call_raw)
                tool_name = call_data.get("name", "unknown")
                tool_call_value = json.dumps(call_data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                # 尝试 XML 格式解析
                tool_name = _extract_xml_tool_name(call_raw)
                tool_call_value = call_raw

            conversations.append({
                "from": "tool_call",
                "value": tool_call_value,
                "tool_name": tool_name,
            })

            last_end = match.end()

        if found_any:
            text_after = final_result[last_end:].strip()
            if text_after:
                conversations.append({"from": "gpt", "value": text_after})

    # 如果没有任何工具调用，整个 finalResult 就是一个 gpt 回复
    if len(conversations) == 2 and final_result.strip():
        conversations.append({"from": "gpt", "value": final_result.strip()})

    return {"conversations": conversations}


def _extract_xml_tool_name(raw: str) -> str:
    """从 XML 格式的 tool_call 内容中提取工具名称"""
    m = re.search(r'<tool_name>\s*(.*?)\s*</tool_name>', raw)
    if m:
        return m.group(1)
    return "unknown"


# ======================================================================
# 6. 完整导出流程
# ======================================================================

def export_sharegpt(
    data_root: str,
    snapshot_file: str,
    output_path: Optional[str] = None,
    include_raw: bool = False,
    session_limit: int = 10,
) -> Optional[str]:
    """
    主导出函数：对比快照 → 提取新增 Sub Agent → 转换 ShareGPT → 保存文件

    Returns:
        导出文件路径，若无新增记录则返回 None
    """
    # 1. 加载旧快照
    print("1️⃣  加载快照...", flush=True)
    old_snapshot = load_snapshot(snapshot_file)
    if not old_snapshot:
        print("   ❌ 未找到快照文件！请先运行 snapshot 命令。", flush=True)
        print(f"   快照路径: {snapshot_file}", flush=True)
        return None

    snap_time = old_snapshot.get("timestamp", "?")
    snap_sessions = old_snapshot.get("sessions", {})
    snap_total_msgs = sum(s.get("message_count", 0) for s in snap_sessions.values())
    print(f"   快照时间: {snap_time}", flush=True)
    print(f"   快照会话数: {len(snap_sessions)}", flush=True)
    print(f"   快照总消息: {snap_total_msgs}", flush=True)

    # 2. 对比，找出新增消息
    print("\n2️⃣  对比消息差异...", flush=True)
    new_messages = find_new_messages(data_root, old_snapshot, session_limit)
    print(f"   新增消息总数: {len(new_messages)}", flush=True)

    if not new_messages:
        print("   ⚠️ 没有发现新增消息", flush=True)
        return None

    # 统计新增消息类型
    role_counts = {}
    for _, _, meta in new_messages:
        role = meta.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
    for role, count in role_counts.items():
        print(f"      {role}: {count}", flush=True)

    # 3. 从新增消息中提取 Sub Agent 记录
    print("\n3️⃣  提取 Sub Agent 记录...", flush=True)
    records = extract_subagent_from_new_messages(new_messages)
    print(f"   发现 {len(records)} 个 Sub Agent 执行记录", flush=True)

    if not records:
        print("   ⚠️ 新增消息中没有 Sub Agent (task) 记录", flush=True)
        return None

    for i, rec in enumerate(records, 1):
        print(f"   [{i}] {rec['subagent_name']}: {rec.get('description', 'N/A')[:60]}", flush=True)

    # 4. 转换为 ShareGPT 格式
    print("\n4️⃣  转换为 ShareGPT 格式...", flush=True)
    sharegpt_data = []
    for rec in records:
        sharegpt_entry = parse_final_result_to_sharegpt(
            final_result=rec["final_result"],
            subagent_name=rec["subagent_name"],
            prompt=rec.get("prompt", ""),
            description=rec.get("description", ""),
        )

        # 添加元信息
        sharegpt_entry["metadata"] = {
            "subagent_name": rec["subagent_name"],
            "description": rec.get("description", ""),
            "tool_call_id": rec.get("tool_call_id", ""),
            "msg_id": rec.get("msg_id", ""),
            "usage": rec.get("usage", {}),
            "tool_call_brief": rec.get("tool_call_brief", ""),
            "export_time": datetime.now().isoformat(),
        }

        if include_raw:
            sharegpt_entry["raw_final_result"] = rec["final_result"]

        conversation_count = len(sharegpt_entry["conversations"])
        tool_calls = sum(1 for c in sharegpt_entry["conversations"] if c["from"] == "tool_call")
        print(f"   [{rec['subagent_name']}] → {conversation_count} turns, "
              f"{tool_calls} tool calls", flush=True)

        sharegpt_data.append(sharegpt_entry)

    # 5. 保存文件
    print("\n5️⃣  保存导出文件...", flush=True)
    if not output_path:
        os.makedirs(DEFAULT_CONFIG["EXPORT_DIR"], exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = os.path.join(
            DEFAULT_CONFIG["EXPORT_DIR"],
            f"{timestamp}_subagents_sharegpt.json"
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sharegpt_data, f, ensure_ascii=False, indent=2)

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"   ✅ 导出完成:", flush=True)
    print(f"   文件: {output_path}", flush=True)
    print(f"   大小: {file_size_kb:.2f} KB", flush=True)
    print(f"   Sub Agent 数: {len(sharegpt_data)}", flush=True)
    print(f"   总 conversations: {sum(len(e['conversations']) for e in sharegpt_data)}", flush=True)

    return output_path


# ======================================================================
# 6b. 分拆导出（每条记录单独保存）
# ======================================================================

def export_split(
    data_root: str,
    snapshot_file: str,
    output_dir: str,
    include_raw: bool = False,
    session_limit: int = 10,
    agent_filter: Optional[str] = None,
) -> List[str]:
    """
    分拆导出：对比快照 → 提取新增 Sub Agent → 每条记录单独保存到指定目录。

    文件命名为 record_0_run_log.json, record_1_run_log.json, ...
    编排器可根据内容中的 prompt 匹配到对应 case，再 rename 为 case_N_run_log.json。

    Args:
        data_root: CodeBuddy 数据根目录
        snapshot_file: 快照文件路径
        output_dir: 输出目录
        include_raw: 是否包含原始 finalResult
        session_limit: 扫描会话数
        agent_filter: 只导出指定名称的 Sub Agent（可选）

    Returns:
        保存的文件路径列表
    """
    # 1. 加载旧快照
    print("1️⃣  加载快照...", flush=True)
    old_snapshot = load_snapshot(snapshot_file)
    if not old_snapshot:
        print("   ❌ 未找到快照文件！请先运行 snapshot 命令。", flush=True)
        print(f"   快照路径: {snapshot_file}", flush=True)
        return []

    snap_time = old_snapshot.get("timestamp", "?")
    print(f"   快照时间: {snap_time}", flush=True)

    # 2. 对比，找出新增消息
    print("\n2️⃣  对比消息差异...", flush=True)
    new_messages = find_new_messages(data_root, old_snapshot, session_limit)
    print(f"   新增消息总数: {len(new_messages)}", flush=True)

    if not new_messages:
        print("   ⚠️ 没有发现新增消息", flush=True)
        return []

    # 3. 提取 Sub Agent 记录
    print("\n3️⃣  提取 Sub Agent 记录...", flush=True)
    records = extract_subagent_from_new_messages(new_messages)

    # 可选：按名称筛选
    if agent_filter:
        records = [r for r in records if r["subagent_name"] == agent_filter]
        print(f"   筛选 agent_filter='{agent_filter}' 后: {len(records)} 条", flush=True)
    else:
        print(f"   发现 {len(records)} 个 Sub Agent 执行记录", flush=True)

    if not records:
        print("   ⚠️ 没有匹配的 Sub Agent 记录", flush=True)
        return []

    # 4. 逐条转换并保存
    print(f"\n4️⃣  分拆保存到 {output_dir} ...", flush=True)
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    for idx, rec in enumerate(records):
        sharegpt_entry = parse_final_result_to_sharegpt(
            final_result=rec["final_result"],
            subagent_name=rec["subagent_name"],
            prompt=rec.get("prompt", ""),
            description=rec.get("description", ""),
        )

        sharegpt_entry["metadata"] = {
            "subagent_name": rec["subagent_name"],
            "description": rec.get("description", ""),
            "tool_call_id": rec.get("tool_call_id", ""),
            "msg_id": rec.get("msg_id", ""),
            "usage": rec.get("usage", {}),
            "tool_call_brief": rec.get("tool_call_brief", ""),
            "export_time": datetime.now().isoformat(),
            "record_index": idx,
        }

        if include_raw:
            sharegpt_entry["raw_final_result"] = rec["final_result"]

        filename = f"record_{idx}_run_log.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sharegpt_entry, f, ensure_ascii=False, indent=2)

        conversation_count = len(sharegpt_entry["conversations"])
        tool_calls = sum(1 for c in sharegpt_entry["conversations"] if c["from"] == "tool_call")
        file_size_kb = os.path.getsize(filepath) / 1024
        print(f"   [{idx}] {rec['subagent_name']}: {conversation_count} turns, "
              f"{tool_calls} tool calls → {filename} ({file_size_kb:.1f} KB)", flush=True)

        saved_files.append(filepath)

    print(f"\n   ✅ 共保存 {len(saved_files)} 个文件到 {output_dir}", flush=True)
    return saved_files


# ======================================================================
# 7. CLI 入口
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description='SubAgent ShareGPT 格式导出器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用流程:
  ┌────────────────────────────────────────────────────────────────────┐
  │ 步骤1: 执行前记录快照                                               │
  │   ./venv/bin/python scripts/subagent_sharegpt_exporter.py snapshot  │
  │                                                                      │
  │ 步骤2: 执行你的 Sub Agent 任务                                       │
  │   （在 CodeBuddy 中正常使用 Sub Agent）                               │
  │                                                                      │
  │ 步骤3: 执行后导出 ShareGPT 记录                                      │
  │   ./venv/bin/python scripts/subagent_sharegpt_exporter.py export     │
  └────────────────────────────────────────────────────────────────────┘

示例:
  # 快照
  ./venv/bin/python scripts/subagent_sharegpt_exporter.py snapshot

  # 导出（合并为单个文件，保存到 logs/sharegpt_exports/）
  ./venv/bin/python scripts/subagent_sharegpt_exporter.py export

  # 导出到指定文件
  ./venv/bin/python scripts/subagent_sharegpt_exporter.py export -o my_export.json

  # 分拆导出（每条记录单独保存，用于 test_agent 流程）
  ./venv/bin/python scripts/subagent_sharegpt_exporter.py export-split -d output_dir/

  # 分拆导出 + 按 Agent 名称筛选
  ./venv/bin/python scripts/subagent_sharegpt_exporter.py export-split -d output_dir/ -a cls-log-agent

  # 导出时包含原始 finalResult
  ./venv/bin/python scripts/subagent_sharegpt_exporter.py export --raw
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 公共参数
    def add_common_args(sub_parser):
        sub_parser.add_argument('--sessions', type=int, default=10,
                                help='扫描最近多少个会话（默认10）')
        sub_parser.add_argument('--snapshot-file',
                                default=DEFAULT_CONFIG['SNAPSHOT_FILE'],
                                help='快照文件路径')
        sub_parser.add_argument('--data-root',
                                default=DEFAULT_CONFIG['CODEBUDDY_DATA_ROOT'],
                                help='CodeBuddy 数据根目录')

    # ── snapshot 子命令 ──
    snap_parser = subparsers.add_parser('snapshot', help='记录当前消息快照（执行 Sub Agent 前调用）')
    add_common_args(snap_parser)

    # ── export 子命令 ──
    exp_parser = subparsers.add_parser('export', help='导出新增 Sub Agent 记录为 ShareGPT 格式（合并为单个文件）')
    exp_parser.add_argument('--output', '-o',
                            help='输出文件路径（默认自动生成带时间戳的文件名）')
    exp_parser.add_argument('--raw', action='store_true',
                            help='同时包含原始 finalResult')
    add_common_args(exp_parser)

    # ── export-split 子命令 ──
    split_parser = subparsers.add_parser(
        'export-split',
        help='导出新增 Sub Agent 记录，每条单独保存（用于 test_agent 流程）')
    split_parser.add_argument('--output-dir', '-d', required=True,
                              help='输出目录（每条记录保存为 record_N_run_log.json）')
    split_parser.add_argument('--agent-filter', '-a',
                              help='只导出指定名称的 Sub Agent（如 cls-log-agent）')
    split_parser.add_argument('--raw', action='store_true',
                              help='同时包含原始 finalResult')
    add_common_args(split_parser)

    # ── info 子命令 ──
    info_parser = subparsers.add_parser('info', help='查看当前快照信息')
    info_parser.add_argument('--snapshot-file',
                             default=DEFAULT_CONFIG['SNAPSHOT_FILE'],
                             help='快照文件路径')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    print("=" * 70, flush=True)
    print("📸 SubAgent ShareGPT 导出器 v1.0", flush=True)
    print("=" * 70, flush=True)
    print(f"命令: {args.command}", flush=True)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)

    try:
        # ── snapshot ──
        if args.command == 'snapshot':
            take_snapshot(
                data_root=args.data_root,
                snapshot_file=args.snapshot_file,
                session_limit=args.sessions,
            )
            print(f"\n{'=' * 70}", flush=True)
            print("✅ 快照完成！现在可以去执行你的 Sub Agent 任务了。", flush=True)
            print(f"   完成后运行: python3 tools/subagent_sharegpt_exporter.py export", flush=True)
            print(f"{'=' * 70}", flush=True)
            return 0

        # ── export ──
        elif args.command == 'export':
            result = export_sharegpt(
                data_root=args.data_root,
                snapshot_file=args.snapshot_file,
                output_path=args.output,
                include_raw=args.raw,
                session_limit=args.sessions,
            )
            print(f"\n{'=' * 70}", flush=True)
            if result:
                print(f"✅ ShareGPT 导出完成: {result}", flush=True)
            else:
                print("⚠️ 没有新增的 Sub Agent 记录可导出", flush=True)
            print(f"{'=' * 70}", flush=True)
            return 0

        # ── export-split ──
        elif args.command == 'export-split':
            saved = export_split(
                data_root=args.data_root,
                snapshot_file=args.snapshot_file,
                output_dir=args.output_dir,
                include_raw=args.raw,
                session_limit=args.sessions,
                agent_filter=args.agent_filter,
            )
            print(f"\n{'=' * 70}", flush=True)
            if saved:
                print(f"✅ 分拆导出完成: {len(saved)} 个文件 → {args.output_dir}", flush=True)
            else:
                print("⚠️ 没有新增的 Sub Agent 记录可导出", flush=True)
            print(f"{'=' * 70}", flush=True)
            return 0

        # ── info ──
        elif args.command == 'info':
            snapshot = load_snapshot(args.snapshot_file)
            if not snapshot:
                print("❌ 未找到快照文件", flush=True)
                print(f"   路径: {args.snapshot_file}", flush=True)
                return 1

            print(f"📸 快照信息:", flush=True)
            print(f"   文件: {args.snapshot_file}", flush=True)
            print(f"   时间: {snapshot.get('timestamp', '?')}", flush=True)
            sessions = snapshot.get('sessions', {})
            print(f"   会话数: {len(sessions)}", flush=True)
            total = sum(s.get('message_count', 0) for s in sessions.values())
            print(f"   总消息: {total}", flush=True)
            print(flush=True)
            for path, info in sessions.items():
                session_id = os.path.basename(os.path.dirname(path))
                print(f"   📋 {session_id}: {info.get('message_count', 0)} 消息", flush=True)
            return 0

    except Exception as e:
        print(f"\n❌ 错误: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
