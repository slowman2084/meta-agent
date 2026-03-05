#!/usr/bin/env bash
#
# Hook 触发的 prompt 同步脚本。
# 当 source/[AgentName]/prompt.md 被编辑后，自动同步到所有 IDE 的 agent 文件。
#
# 工作方式：
#   1. 从 stdin 读取 hook payload JSON
#   2. 提取被编辑的文件路径
#   3. 如果是 source/*/prompt.md，执行同步
#
# 兼容：
#   - Cursor (afterFileEdit): payload.filepath
#   - Claude Code / CodeBuddy (PostToolUse): payload.tool_input.file_path
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_FILE="$HOME/.agent_factory/sync_prompt.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

PAYLOAD=$(cat)

# 从 payload 中提取被编辑的文件路径（兼容不同 IDE 的 payload 格式）
EDITED_FILE=$(echo "$PAYLOAD" | python3 -c "
import sys, json
try:
    p = json.load(sys.stdin)
    # Claude Code / CodeBuddy: PostToolUse
    path = p.get('tool_input', {}).get('file_path', '')
    if not path:
        # Cursor: afterFileEdit
        path = p.get('filepath', '') or p.get('file_path', '')
    print(path)
except:
    print('')
" 2>/dev/null)

if [[ -z "$EDITED_FILE" ]]; then
    log "No file path in payload, skipping"
    echo '{}'
    exit 0
fi

# 转为绝对路径
if [[ "$EDITED_FILE" != /* ]]; then
    EDITED_FILE="$PROJECT_ROOT/$EDITED_FILE"
fi

# 检查是否是 source/*/prompt.md
if [[ ! "$EDITED_FILE" =~ source/([^/]+)/prompt\.md$ ]]; then
    echo '{}'
    exit 0
fi

AGENT_NAME="${BASH_REMATCH[1]}"
PROMPT_FILE="$PROJECT_ROOT/source/$AGENT_NAME/prompt.md"

if [[ ! -f "$PROMPT_FILE" ]]; then
    log "Prompt file not found: $PROMPT_FILE"
    echo '{}'
    exit 0
fi

log "Syncing $AGENT_NAME prompt to all IDEs..."

# 读取各 IDE 现有文件的文件头（YAML frontmatter）
extract_header() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        return
    fi
    # 提取 --- 到 --- 之间的内容（含两行 ---）
    awk '/^---$/{n++} n<=2{print} n==2{exit}' "$file"
}

sync_to_ide() {
    local target="$1"
    local target_dir
    target_dir="$(dirname "$target")"

    if [[ ! -d "$target_dir" ]]; then
        log "  Target dir not found: $target_dir, skipping"
        return
    fi

    if [[ -f "$target" ]]; then
        local header
        header=$(extract_header "$target")
        if [[ -n "$header" ]]; then
            { echo "$header"; echo ""; cat "$PROMPT_FILE"; } > "$target"
            log "  Synced: $target (preserved header)"
        else
            cp "$PROMPT_FILE" "$target"
            log "  Synced: $target (no header)"
        fi
    else
        log "  Target not found: $target, skipping"
    fi
}

sync_to_ide "$PROJECT_ROOT/.cursor/agents/$AGENT_NAME.md"
sync_to_ide "$PROJECT_ROOT/.codebuddy/agents/$AGENT_NAME.md"
sync_to_ide "$PROJECT_ROOT/.claude/agents/$AGENT_NAME.md"

log "Sync complete for $AGENT_NAME"

echo '{}'
