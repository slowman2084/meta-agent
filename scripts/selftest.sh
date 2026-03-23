#!/usr/bin/env bash
#
# Agent Factory 自检脚本
#
# 在 IDE 之外通过 CLI 工具调用 Agent，验证其基本能力。
# 支持 claude (Claude Code CLI) 和 codebuddy 两个 CLI 后端。
#
# 用法:
#   ./scripts/selftest.sh <agent_name> [options]
#
# 选项:
#   --cli <claude|codebuddy>   指定 CLI 后端 (默认: 自动检测)
#   --csv <path>               CSV 测试用例文件 (默认: source/<agent>/testcases.csv)
#   --cases <n>                只测试前 N 条用例 (默认: 全部)
#   --timeout <seconds>        单条用例超时时间 (默认: 120)
#   --eval                     同时运行 eval-judge 评估
#   --dry-run                  只显示将要执行的命令，不实际运行
#   -h, --help                 显示帮助
#
# 示例:
#   ./scripts/selftest.sh my-agent --cli claude --cases 3
#   ./scripts/selftest.sh code-reviewer --cli codebuddy --eval
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 默认值 ──────────────────────────────────────────────
CLI_BACKEND=""
CSV_FILE=""
MAX_CASES=0
TIMEOUT=120
RUN_EVAL=false
DRY_RUN=false
AGENT_NAME=""

# ── 颜色 ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
    exit 0
}

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

# ── 参数解析 ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --cli) CLI_BACKEND="$2"; shift 2 ;;
        --csv) CSV_FILE="$2"; shift 2 ;;
        --cases) MAX_CASES="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --eval) RUN_EVAL=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        -*) log_error "未知选项: $1"; exit 1 ;;
        *) AGENT_NAME="$1"; shift ;;
    esac
done

if [[ -z "$AGENT_NAME" ]]; then
    log_error "必须指定 agent 名称"
    echo "用法: $0 <agent_name> [options]"
    exit 1
fi

# ── 自动检测 CLI ────────────────────────────────────────
detect_cli() {
    if [[ -n "$CLI_BACKEND" ]]; then
        return
    fi
    if command -v claude &>/dev/null; then
        CLI_BACKEND="claude"
        log_info "自动检测到 Claude Code CLI"
    elif command -v codebuddy &>/dev/null; then
        CLI_BACKEND="codebuddy"
        log_info "自动检测到 codebuddy CLI"
    else
        log_error "未找到 claude 或 codebuddy CLI，请确认已安装"
        exit 1
    fi
}

# ── 路径解析 ────────────────────────────────────────────
resolve_paths() {
    local agent_dir="$PROJECT_ROOT/source/$AGENT_NAME"
    if [[ ! -d "$agent_dir" ]]; then
        log_error "Agent 目录不存在: $agent_dir"
        exit 1
    fi

    PROMPT_FILE="$agent_dir/prompt.md"
    if [[ ! -f "$PROMPT_FILE" ]]; then
        log_error "提示词文件不存在: $PROMPT_FILE"
        exit 1
    fi

    if [[ -z "$CSV_FILE" ]]; then
        CSV_FILE="$agent_dir/testcases.csv"
    fi
    if [[ ! -f "$CSV_FILE" ]]; then
        log_error "测试用例文件不存在: $CSV_FILE"
        exit 1
    fi

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    OUTPUT_DIR="$agent_dir/tmp/selftest_${TIMESTAMP}"
    mkdir -p "$OUTPUT_DIR"
}

# ── CSV 解析 ────────────────────────────────────────────
# 简易 CSV 解析，支持双引号包裹的多行字段
parse_csv() {
    python3 - "$CSV_FILE" "$MAX_CASES" <<'PYEOF'
import csv, sys, json

csv_file = sys.argv[1]
max_cases = int(sys.argv[2])

with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    cases = []
    for i, row in enumerate(reader):
        if max_cases > 0 and i >= max_cases:
            break
        cases.append({
            "index": i + 1,
            "input": row.get("Input", "").strip(),
            "expected": row.get("ExpectedOutput", "").strip(),
            "judge": row.get("Judge", "").strip()
        })

print(json.dumps(cases, ensure_ascii=False))
PYEOF
}

# ── 调用 Agent ──────────────────────────────────────────
invoke_agent() {
    local input="$1"
    local output_file="$2"

    case "$CLI_BACKEND" in
        claude)
            # claude 支持 --agent 直接指定 .claude/agents/ 中的 agent
            if [[ "$DRY_RUN" == true ]]; then
                echo "[DRY-RUN] echo '<input>' | claude -p --agent $AGENT_NAME --dangerously-skip-permissions --max-turns 30"
                return 0
            fi
            echo "$input" | timeout "$TIMEOUT" claude \
                -p \
                --agent "$AGENT_NAME" \
                --dangerously-skip-permissions \
                --max-turns 30 \
                2>/dev/null > "$output_file" || true
            ;;
        codebuddy)
            # codebuddy 使用 --system-prompt-file 加载提示词
            if [[ "$DRY_RUN" == true ]]; then
                echo "[DRY-RUN] echo '<input>' | codebuddy -p --system-prompt-file $PROMPT_FILE --dangerously-skip-permissions"
                return 0
            fi
            echo "$input" | timeout "$TIMEOUT" codebuddy \
                -p \
                --system-prompt-file "$PROMPT_FILE" \
                --dangerously-skip-permissions \
                --max-turns 30 \
                2>/dev/null > "$output_file" || true
            ;;
        *)
            log_error "不支持的 CLI 后端: $CLI_BACKEND"
            return 1
            ;;
    esac
}

# ── 调用 eval-judge ─────────────────────────────────────
invoke_eval() {
    local input="$1"
    local expected="$2"
    local judge="$3"
    local actual="$4"
    local eval_file="$5"

    local eval_prompt
    eval_prompt=$(cat <<EVALEOF
【Input】
${input}

【ExpectedOutput】
${expected}

【Judge】
${judge}

【ActualOutput】
${actual}
EVALEOF
)

    case "$CLI_BACKEND" in
        claude)
            echo "$eval_prompt" | timeout "$TIMEOUT" claude \
                -p \
                --agent "eval-judge" \
                --dangerously-skip-permissions \
                --max-turns 5 \
                2>/dev/null > "$eval_file" || true
            ;;
        codebuddy)
            local eval_prompt_file="$PROJECT_ROOT/source/eval-judge/prompt.md"
            echo "$eval_prompt" | timeout "$TIMEOUT" codebuddy \
                -p \
                --system-prompt-file "$eval_prompt_file" \
                --dangerously-skip-permissions \
                --max-turns 5 \
                2>/dev/null > "$eval_file" || true
            ;;
    esac
}

# ── 主流程 ──────────────────────────────────────────────
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   Agent Factory Self-Test                ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""

    detect_cli
    resolve_paths

    log_info "Agent:     $AGENT_NAME"
    log_info "CLI:       $CLI_BACKEND"
    log_info "CSV:       $CSV_FILE"
    log_info "输出目录:  $OUTPUT_DIR"
    log_info "超时:      ${TIMEOUT}s"
    log_info "评估模式:  $RUN_EVAL"
    echo ""

    # 设置上下文（可选，set_context.py 已移至 deprecated/）
    # python3 "$SCRIPT_DIR/set_context.py" test_agent "$AGENT_NAME" "selftest_${TIMESTAMP}"

    # 解析 CSV
    log_step "解析测试用例..."
    local cases_json
    cases_json=$(parse_csv)
    local total
    total=$(echo "$cases_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
    log_info "共 $total 条用例"
    echo ""

    # 汇总变量
    local passed=0
    local failed=0
    local errors=0
    local summary_file="$OUTPUT_DIR/summary.md"

    echo "# Self-Test Report" > "$summary_file"
    echo "" >> "$summary_file"
    echo "- Agent: $AGENT_NAME" >> "$summary_file"
    echo "- CLI: $CLI_BACKEND" >> "$summary_file"
    echo "- Time: $(date '+%Y-%m-%d %H:%M:%S')" >> "$summary_file"
    echo "- CSV: $CSV_FILE" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "| # | Input (前30字) | 状态 | 输出长度 | 评分 |" >> "$summary_file"
    echo "|---|---|---|---|---|" >> "$summary_file"

    # 逐条测试
    echo "$cases_json" | python3 -c "
import sys, json
cases = json.load(sys.stdin)
for c in cases:
    print(json.dumps(c, ensure_ascii=False))
" | while IFS= read -r case_line; do
        local idx input expected judge
        idx=$(echo "$case_line" | python3 -c "import sys,json; print(json.load(sys.stdin)['index'])")
        input=$(echo "$case_line" | python3 -c "import sys,json; print(json.load(sys.stdin)['input'])")
        expected=$(echo "$case_line" | python3 -c "import sys,json; print(json.load(sys.stdin)['expected'])")
        judge=$(echo "$case_line" | python3 -c "import sys,json; print(json.load(sys.stdin)['judge'])")

        local input_preview="${input:0:40}"
        log_step "[$idx/$total] 测试: ${input_preview}..."

        local output_file="$OUTPUT_DIR/case_${idx}_output.txt"
        local eval_file="$OUTPUT_DIR/case_${idx}_eval.txt"

        # 调用 Agent
        local start_time
        start_time=$(date +%s)
        invoke_agent "$input" "$output_file"
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        # 检查输出
        local output_len=0
        local status="ERROR"
        local score="-"

        if [[ -f "$output_file" ]]; then
            output_len=$(wc -c < "$output_file" | tr -d ' ')
            if [[ "$output_len" -gt 10 ]]; then
                status="OK"
                log_ok "用例 $idx 完成 (${duration}s, ${output_len} bytes)"
                ((passed++)) || true
            else
                status="EMPTY"
                log_warn "用例 $idx 输出过短 (${output_len} bytes)"
                ((failed++)) || true
            fi
        else
            log_error "用例 $idx 无输出文件"
            ((errors++)) || true
        fi

        # 可选评估
        if [[ "$RUN_EVAL" == true && "$status" == "OK" && -n "$judge" ]]; then
            log_step "  评估用例 $idx..."
            local actual
            actual=$(cat "$output_file")
            invoke_eval "$input" "$expected" "$judge" "$actual" "$eval_file"

            if [[ -f "$eval_file" ]]; then
                score=$(grep -oP '总分[：:]\s*\K\d+' "$eval_file" 2>/dev/null | head -1 || echo "-")
                [[ -n "$score" ]] && log_info "  评分: $score"
            fi
        fi

        echo "| $idx | ${input_preview:0:30} | $status | $output_len | $score |" >> "$summary_file"
    done

    # 清理上下文（可选）
    # python3 "$SCRIPT_DIR/set_context.py" clear

    echo ""
    echo -e "${CYAN}══════════════════════════════════════════${NC}"
    log_info "测试完成！结果保存在: $OUTPUT_DIR"
    log_info "汇总报告: $OUTPUT_DIR/summary.md"
    echo -e "${CYAN}══════════════════════════════════════════${NC}"
}

main "$@"
