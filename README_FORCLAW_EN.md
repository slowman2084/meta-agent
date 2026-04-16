# Teach AI to Write Golden Lines in 5 Minutes — Meta-Agent Quick Start

> **⏱️ Estimated Time**: Environment setup 5 min + Workflow experience 20–30 min (depending on execution method)
>
> You'll use 5 "pop song golden lines" test cases to experience the full Agent creation, testing, and iterative optimization workflow.
> 
> **OpenClaw Users**: No installation needed — clone the project and complete the entire workflow in your browser.

---

### 📖 Design Principles

**CLI / IDE Approach**: Each step is an independent CLI call (`-p` mode). After each step **completes**, read the generated files and showcase interesting content to the user.

**OpenClaw Approach**: Each step is completed via spawn sub agent. You (OpenClaw) read `source/meta-*/prompt.md` as the system prompt for each sub agent, granting `file_read`, `file_write`, `list_directory` tools via the `tools` parameter when spawning. Intermediate artifacts (prompts, outputs, scores) are **written to the file system**, sharing the same directory structure (`source/[AgentName]/`) as CLI / IDE.

The sense of achievement comes from "seeing what AI specifically wrote, what golden lines it created, how scores changed" — not just a "Done" message.

**Golden Lines Evaluation Logic**: The Agent must **originate** **10 candidate golden lines** each time. Scoring primarily checks **originality** (no copying existing lyrics), **imagery alignment** (whether it captures the emotional core of the keywords), and **literary quality** (rhetoric, rhythm, imagery). ExpectedOutput serves as a style benchmark — evaluation checks whether **at least 1 of the Agent's original 10 lines reaches the benchmark level**.

### 🚨 Three Iron Rules (OpenClaw Must Obey)

> **Iron Rule 1: Test cases are the yardstick — never modify them.**
>
> The 5 test cases (Input + ExpectedOutput + Judge) become fixed evaluation standards after Step 2. Throughout the entire iteration process, you **must never modify, adjust, or replace any test case content**. Even if eval-judge's reports flag `[rubric]` (rubric may be unreasonable) or `[testcase]` (ExpectedOutput may be incorrect), you **must absolutely not modify test cases or scoring criteria based on this**. The only thing you're allowed to change is **the Agent's prompt**. If a test case consistently scores low, the prompt isn't good enough yet — keep optimizing the prompt, don't lower the bar.
>
> **Iron Rule 2: Optimization must ensure generalizability — no overfitting.**
>
> The goal of iterative optimization is to improve the Agent's **general capabilities**, not to make it "memorize" answers for these 5 cases. Each prompt optimization must ensure changes are equally effective for **inputs never seen before**. Specifically: no embedding few-shot examples highly similar to test cases in the prompt; no special handling for specific keywords from certain cases; all changes must be general capability improvements (reasoning frameworks, format specifications, edge case handling, etc.).
>
> **Iron Rule 3: Fully automated execution — don't stop to ask the user.**
>
> Unless encountering an unrecoverable error (e.g., sub agent spawn failure), **do not stop to ask the user "should I continue" or "proceed to next step?"**. The entire flow from Step 2 through Step 5 should execute seamlessly and automatically. After each step completes, display results and immediately proceed to the next step. The user choosing to execute this document means authorizing you to complete the entire workflow automatically.

---

## 🎯 What You'll Accomplish

```
5 lyrics golden-line test cases (each requiring the Agent to originate 10 candidate golden lines)
    → AI reverse-engineers a prompt (see how it understands "original golden lines")
    → First test: see which 10 golden lines the Agent wrote for each query (actual content!)
    → 3 rounds of iterative optimization, each round showing prompt changes and score improvements
    → Final comparison: initial vs. final prompt, understanding AI's optimization strategy
```

---

## Prerequisites

### Choose Your Experience Mode

Meta-Agent supports three experience modes — pick **any one**:

| Mode | Installation Required | Best For | Completeness |
|------|----------------------|----------|-------------|
| **🅰️ OpenClaw** | None (browser only) | Quick exploration without setup | ⭐⭐⭐⭐⭐ |
| **🅱️ AI IDE** | Cursor / CodeBuddy / Claude Code | Developers with existing IDEs | ⭐⭐⭐⭐⭐ |
| **🅲 CLI** | CodeBuddy CLI or Claude Code CLI | Terminal and scripting enthusiasts | ⭐⭐⭐⭐⭐ |

#### 🅰️ OpenClaw (Zero Barrier)

**No tools need to be installed.** OpenClaw calls Meta-Agent's sub agents (such as meta-prompt-engineer, meta-eval-judge, etc.) via sub agent spawn, granting `file_read`, `file_write`, `list_directory` tools via the `tools` parameter.

How it works:
- This document (`README_FORCLAW_EN.md`) itself is OpenClaw's execution handbook
- OpenClaw reads `source/meta-*/prompt.md` as the system prompt for each sub agent
- Completes the full **prompt generation → evaluation scoring → iterative optimization** workflow via sub agent spawn
- Orchestration rules are embedded in the step-by-step instructions in this document — no separate IDE installation needed
- Each sub agent has a specific input format (using `【】` format markers); this document provides exact templates at each step
- **File read/write capability via spawn**: When spawning each sub agent, grant `file_read`, `file_write`, `list_directory` tools via the `tools` parameter. This allows sub agents to directly read/write the local file system, with artifacts written to `source/[AgentName]/` directory, sharing the same directory structure as CLI / IDE

> 💡 **Difference from CLI / IDE**: OpenClaw doesn't support MCP tool calling or shell command execution, but the file read/write tools granted during spawn allow it to complete the entire demo workflow. Agents requiring MCP (like log analysis) still need CLI or IDE.

#### 🅱️ IDE Mode

Open the project directly in your IDE (Cursor / CodeBuddy / Claude Code) and type trigger words (e.g., `create agent`) in the chat. The IDE automatically loads rules and sub agent configurations.

#### 🅲 CLI Mode

| CLI Tool | Installation | Notes |
|---------|-------------|-------|
| **CodeBuddy CLI** | Included with CodeBuddy IDE | Recommended, most complete experience |
| **Claude Code CLI** | `npm install -g @anthropic-ai/claude-code` | Requires Anthropic API Key |

---

## Step 0: Environment Setup

### 🅰️ OpenClaw

**Clone the project locally** (OpenClaw grants file read/write tools when spawning sub agents, requiring a local workspace):

```bash
git clone <your-repo-url>
cd meta-agent
```

> 💡 No need to create a virtual environment or install Python dependencies. OpenClaw only needs to read prompt files (`source/meta-*/prompt.md`) from the repository and write artifacts to the `source/` directory.
>
> If OpenClaw cannot directly access the local file system, you can also read prompt files via `web_fetch` from GitHub Raw URLs:

| Sub Agent | GitHub Raw URL |
|-----------|---------------|
| Prompt Generation/Optimization Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-prompt-engineer/prompt.md` |
| Prompt Anti-cheat Review Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-reviewer/prompt.md` |
| Evaluation Scoring Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-eval-judge/prompt.md` |
| Scoring Criteria Generation Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-rubric-gen/prompt.md` |

### 🅱️🅲 CLI / IDE

```bash
git clone <your-repo-url>
cd meta-agent
```

**Read and execute [SETUP.md](SETUP.md) Steps 1–3** (create virtual environment → install dependencies → distribute rules and built-in Agents).

Verify after completion:
```bash
./venv/bin/python scripts/verify_setup.py
```

All key items should show ✅. MCP items showing ⚠️ is normal — this demo doesn't need them.

Confirm you have **at least one** of these CLI tools available:

```bash
# Check CodeBuddy CLI
CodeBuddy --version

# Or check Claude Code CLI
claude --version
```

> This demo **does not need MCP or any additional API Keys**.

---

## Step 1: Prepare Test Cases

### 🅰️ OpenClaw

Same as CLI / IDE — create `demo_testcases.yaml` in the project root (use `file_write` to write the content below).

### 🅱️🅲 CLI / IDE

Create `demo_testcases.yaml` in the project root:

```yaml
meta:
  count: 5
  notice: "Original golden lines assistant demo — Agent must originate 10 candidate golden lines per query (no copying existing lyrics)"
cases:
  - Input: |
      Create 10 original lyric golden lines around the keyword "roller coaster ride" and the theme of love. Requirements: must not copy existing lyrics, must be entirely new creations.
    ExpectedOutput: |
      Style benchmark (reproduction not required, used as imagery and quality reference for evaluation): Baby our love is like a roller coaster ride, shooting me up to the sky then plummeting me down — capture the love imagery of "sudden ups and downs, thrilling yet unsettling"
    Judge: ""

  - Input: |
      Create 10 original lyric golden lines around the keyword "what the world gave me" and the theme of life. Requirements: must not copy existing lyrics, must be entirely new creations.
    ExpectedOutput: |
      Style benchmark (reproduction not required, used as imagery and quality reference for evaluation): The world gave me crickets chirping, and also gave me thunder; gave me a crescent moon, and also gave me evening stars — capture the life imagery of "gifts of contrast and gratitude"
    Judge: ""

  - Input: |
      Create 10 original lyric golden lines around the keyword "every word is a secret crush" and the theme of love. Requirements: must not copy existing lyrics, must be entirely new creations.
    ExpectedOutput: |
      Style benchmark (reproduction not required, used as imagery and quality reference for evaluation): Every word of his never mentioned loving you, yet every sentence of yours says "I'm willing" — capture the love imagery of "unspoken words, feelings left unsaid"
    Judge: ""

  - Input: |
      Create 10 original lyric golden lines around the keyword "a toast to myself" and the theme of life. Requirements: must not copy existing lyrics, must be entirely new creations.
    ExpectedOutput: |
      Style benchmark (reproduction not required, used as imagery and quality reference for evaluation): A toast to myself, from here on I won't look back — capture the life imagery of "self-reconciliation, letting go and moving forward"
    Judge: ""

  - Input: |
      Create 10 original lyric golden lines around the keywords "the moon" and "windowsill". Requirements: must not copy existing lyrics, must be entirely new creations.
    ExpectedOutput: |
      Style benchmark (reproduction not required, used as imagery and quality reference for evaluation): If the moon hasn't risen yet, the streetlamp can also light the windowsill — capture the life imagery of "everyday gentleness amid waiting"
    Judge: ""
```

> 📝 **Core Scoring Logic**: The Agent must **originate** **10 candidate golden lines** (strictly no copying existing lyrics). ExpectedOutput is a style/imagery benchmark — text reproduction is not required. Main scoring dimensions: **originality** (entirely new creations), **imagery alignment** (whether it captures the emotional core of the keywords), **literary quality** (rhetoric, rhythm, imagery). `Judge` is left empty — AI will auto-generate the corresponding scoring rubrics later.

---

## Step 2: Create the Agent from Test Cases

### 🅰️ OpenClaw

First create the Agent directory structure, then spawn 2 sub agents sequentially to complete creation:

**2.0 Create Directory Scaffold**

Use `file_write` to create the following directories and files:
- `source/lyrics-golden-lines/tmp/` (runtime artifacts)
- `source/lyrics-golden-lines/bak/` (backups)
- `source/lyrics-golden-lines/changelog.md` (change log, initially empty)

**2a. Spawn `meta-prompt-engineer`** — Generate the prompt

1. Use `file_read` to read `source/meta-prompt-engineer/prompt.md` as the system prompt
2. Use `file_read` to read `demo_testcases.yaml`, extract Input and ExpectedOutput from all 5 cases
3. Spawn sub agent, **granting `file_read`, `file_write`, `list_directory` via the `tools` parameter**, pass in the following user message (note the `【】` format markers — this is the required input format for this sub agent):

> 💡 **All subsequent spawns grant tools the same way** — not repeated below.

```
【理想态描述】
This Agent's function is: based on user-given keywords and themes, originate 10 high-quality lyric golden lines.
A good original golden-lines Agent should have:
- Accurately understand user intent (emotion, imagery, scenario)
- Consistently output 10 candidate golden lines per query, all original (strictly no copying existing lyrics)
- Golden lines with literary quality (rhetoric, rhythm, imagery)
- At least 1 candidate reaching the ExpectedOutput style benchmark level

【示例用例】
[Read from demo_testcases.yaml, organized per case as follows:]
Input: [cases[i].Input]
→ Best reference: [cases[i].ExpectedOutput]
```

> 💡 Both the ideal state description and example cases are extracted from `demo_testcases.yaml` — no manual hardcoding needed.

🎉 **Extract artifacts from the sub agent's response and write to files**:

- The prompt-engineer's output will contain an `===PROMPT===` marker — the content **after this marker** is the generated Agent prompt
- Write the prompt to `source/lyrics-golden-lines/prompt.md`
- Write the ideal state description to `source/lyrics-golden-lines/ideal_state.md`

**2b. Spawn `meta-rubric-gen`** — Generate scoring criteria for each case

1. Use `file_read` to read `source/meta-rubric-gen/prompt.md` as the system prompt
2. Use `file_read` to read `demo_testcases.yaml`, iterate over each case
3. Spawn **once per case** (one case per spawn), passing in (using `【】` format markers):

```
【Input】
[Read cases[i].Input from demo_testcases.yaml]

【任务约束】
Core scoring logic: Agent must originate 10 candidate golden lines (strictly no copying existing lyrics). Main scoring dimensions: originality (entirely new creations), imagery alignment (whether it captures the emotional core of the keywords), literary quality (rhetoric, rhythm, imagery). Below is the style benchmark (text reproduction not required, used for evaluating imagery and quality level).
Style benchmark: [Read cases[i].ExpectedOutput from demo_testcases.yaml]
```

> **No need to pass agent_name** (this demo has no references directory) — rubric-gen will generate scoring criteria directly based on Input content.

🎉 **Write the 5 Judge scoring criteria back into `demo_testcases.yaml`** in the corresponding `Judge` fields (replacing empty strings). Also copy to `source/lyrics-golden-lines/testcases.yaml`.

**2c. Record Change Log**

Write initial creation record to `source/lyrics-golden-lines/changelog.md`.

> **After Step 2 completes, immediately proceed to Step 3 automatically. Do not stop to ask the user.**

### 🅱️🅲 CLI / IDE

```bash
CodeBuddy --dangerously-skip-permissions -p "
Please execute the create agent workflow:

1. Creation method: c (create from YAML test cases)
2. YAML file path: demo_testcases.yaml
3. Agent name: lyrics-golden-lines
4. Brief description: Based on user-given keywords and themes, originate 10 high-quality lyric golden lines
5. Tool semantics: none (no tools needed)
6. MCP required: no
7. References: not needed, continue directly
8. Need additional test cases: no

Please follow the complete create agent method c workflow, including: analyze cases to extract ideal state, call meta-prompt-engineer to generate prompt, call meta-rubric-gen to generate Judge for each case, run baseline model to fill ExpectedOutput, save to source/lyrics-golden-lines/testcases.yaml, run install.py to distribute.

Note: The core scoring logic for Judge is that the Agent must originate 10 candidate golden lines (strictly no copying existing lyrics). Scoring dimensions are originality, imagery alignment, and literary quality. ExpectedOutput is a style benchmark — text reproduction is not required.
"
```

### 🎉 Creation Complete! (🅱️🅲 CLI / IDE) Read the generated files to see what AI did:

```bash
# 1. AI-written prompt — see how it understands "original golden lines"
cat source/lyrics-golden-lines/prompt.md

# 2. AI-extracted ideal state — what it thinks a good original golden-lines Agent should have
cat source/lyrics-golden-lines/ideal_state.md

# 3. AI-generated scoring criteria (Judge) for each case — see what dimensions it plans to score on
#    (use yaml_tool to read case 0's Judge field, avoiding reading the entire large YAML at once)
./venv/bin/python scripts/yaml_tool.py get source/lyrics-golden-lines/testcases.yaml 0 --fields Judge
```

> 💡 **Display Tip**: Show the core paragraphs of `prompt.md` to the user, letting them see "what creative logic AI derived from 5 golden lines." The Judge should show scoring dimensions like "originate 10 candidate golden lines", "originality", and "imagery alignment." This is the first moment of satisfaction.

---

## Step 3: First Test — See What Golden Lines the Agent Wrote

### 🅰️ OpenClaw

**3a. Spawn `lyrics-golden-lines`** — Get the Agent's actual output

1. Use `file_read` to read `source/lyrics-golden-lines/prompt.md` as the system prompt
2. Use `file_read` to read `source/lyrics-golden-lines/testcases.yaml`, extract 5 Inputs
3. Spawn sub agent, send Inputs **one by one** (just send the case content directly)

Spawn separately for each case or send sequentially within the same agent. Write 5 actual outputs via `file_write`:
- `source/lyrics-golden-lines/tmp/test_initial/case_0_actual_result.txt`
- `source/lyrics-golden-lines/tmp/test_initial/case_1_actual_result.txt`
- ... and so on

**3b. Spawn `meta-eval-judge`** — Evaluate and score each case

1. Use `file_read` to read `source/meta-eval-judge/prompt.md` as the system prompt
2. For each case, read all parameters from files:
   - **Input**: Read `cases[i].Input` from `testcases.yaml`
   - **ExpectedOutput**: Read `cases[i].ExpectedOutput` from `testcases.yaml`
   - **Judge**: Read `cases[i].Judge` from `testcases.yaml`
   - **ActualOutput**: Read from `tmp/test_initial/case_[i]_actual_result.txt`
3. **Spawn once per case** (never merge multiple cases), passing in (using `【】` format markers):

```
【Input】
[Read from testcases.yaml]

【ExpectedOutput】
[Read from testcases.yaml]

【Judge】
[Read from testcases.yaml]

【ActualOutput】
[Read from case_[i]_actual_result.txt]
```

> eval-judge will score against each rubric criterion, outputting a total score and areas for improvement.

🎉 **Write 5 evaluation results to files**:
- `source/lyrics-golden-lines/tmp/test_initial/case_0_eval_result.md`
- ... and so on
- Write aggregated evaluation report to `source/lyrics-golden-lines/tmp/test_initial/评估报告.md`

Show the user each case's golden line creation results and scores.

> 💡 **Display Tip**: Show each case's actual golden line output and evaluation score one by one. Organize as follows (data read from `评估报告.md` and `case_[N]_actual_result.txt`, do not fabricate):
> ```
> 🎵 You asked: [case theme] (10 original lines required)
> 🤖 Agent wrote 10 lines, best one: "[extract best line from actual_result]"
> 📊 Score: [read actual score from eval_result] | [read evaluation comment from eval_result]
> ```
>
> **A first-round score can be anything — that's normal. Remember this score, watch how AI evolves next.**
>
> ⚠️ **Important**: eval-judge reports may flag `[rubric]` (scoring criteria may be unreasonable) or `[testcase]` (reference answer may be incorrect). **Ignore these tags** — do not suggest modifying test cases or scoring criteria. These test cases are fixed yardsticks. From here on, only optimize the prompt to improve scores.
>
> **After displaying evaluation results, immediately proceed to Step 4 — do not ask "should I continue?"**

### 🅱️🅲 CLI / IDE

```bash
CodeBuddy --dangerously-skip-permissions -p "
test lyrics-golden-lines
"
```

### 🎉 Test Complete! (🅱️🅲 CLI / IDE) Read results to see the Agent's specific outputs (10 original candidate golden lines per case):

```bash
# Find the latest test directory
TEST_DIR=$(ls -td source/lyrics-golden-lines/tmp/test_* | head -1)

# ⭐ Most important — see the Agent's actual response for each query:
echo "===== 🎵 Roller Coaster Ride ====="
cat "$TEST_DIR/case_0_actual_result.txt"
echo ""
echo "===== 🎵 What the World Gave Me ====="
cat "$TEST_DIR/case_1_actual_result.txt"
echo ""
echo "===== 🎵 Every Word a Secret Crush ====="
cat "$TEST_DIR/case_2_actual_result.txt"
echo ""
echo "===== 🎵 A Toast to Myself ====="
cat "$TEST_DIR/case_3_actual_result.txt"
echo ""
echo "===== 🎵 The Moon's Everyday Gentleness ====="
cat "$TEST_DIR/case_4_actual_result.txt"

# 📊 Evaluation report — score for each case and areas for improvement
cat "$TEST_DIR/评估报告.md"
```

> 💡 **Display Tip**:
> - Show the actual response for each of the 5 queries **one by one** — this is the most interesting part: "see what 10 original golden lines AI wrote for you"
> - Then show the score table from the evaluation report (core metrics: originality, imagery alignment, literary quality)
> - Organize the display like this (all data read from files, do not fabricate):
>
> ```
> 🎵 You asked: [case theme] (10 original lines required)
> 🤖 Agent wrote 10 lines, best one: "[extract from actual_result]"
> 📊 Score: [read from eval_result] | [read evaluation comment from eval_result]
> ```
>
> **A first-round score can be anything — that's normal. Remember this score, watch how AI evolves next.**

---

## Step 4: Iterative Optimization — Watch AI Evolve

> Each iteration = Run Agent → Evaluate scores → Optimize prompt based on feedback. Repeat for 3 rounds and observe score changes.

### 🅰️ OpenClaw

> 🚨 **Reminder: Re-read the Three Iron Rules**. During iteration, **absolutely do not modify test cases, Judge, or ExpectedOutput**. The `[rubric]` / `[testcase]` tags in eval-judge reports are for diagnostic reference only, **not authorization to modify test cases**. The only thing allowed to change is the Agent's prompt. Also, all 3 rounds should execute **fully automatically and continuously** — do not stop between rounds to ask the user.

All artifacts are persisted via the file system, greatly reducing context pressure:
- Prompt: `source/lyrics-golden-lines/prompt.md` (updated each round)
- Ideal state: `source/lyrics-golden-lines/ideal_state.md` (unchanged)
- Test cases + Judge: `source/lyrics-golden-lines/testcases.yaml` (unchanged)
- Per-round artifacts: `source/lyrics-golden-lines/tmp/iter_[N]/`

**Each iteration executes 3 sub-steps (3 rounds completed automatically without pausing):**

**4a. Run + Evaluate** (same as Step 3, artifacts written to `tmp/iter_[N]/`)

1. Use `file_read` to read current `source/lyrics-golden-lines/prompt.md` as system prompt
2. Use `file_read` to read `source/lyrics-golden-lines/testcases.yaml`, extract each case's Input
3. Spawn `lyrics-golden-lines` sub agent, send 5 Inputs one by one, write outputs to `source/lyrics-golden-lines/tmp/iter_[N]/case_[i]_actual_result.txt`
4. Use `file_read` to read eval-judge's prompt.md as system prompt, spawn evaluation per case — all 4 fields for each evaluation read from files:
   - **Input**: Read `cases[i].Input` from `testcases.yaml`
   - **ExpectedOutput**: Read `cases[i].ExpectedOutput` from `testcases.yaml`
   - **Judge**: Read `cases[i].Judge` from `testcases.yaml`
   - **ActualOutput**: Read from `tmp/iter_[N]/case_[i]_actual_result.txt`
5. Write evaluation results to `source/lyrics-golden-lines/tmp/iter_[N]/case_[i]_eval_result.md`
6. Aggregate into `source/lyrics-golden-lines/tmp/iter_[N]/评估报告.md`

**4b. Optimize the Prompt**

First backup current prompt: copy `source/lyrics-golden-lines/prompt.md` to `source/lyrics-golden-lines/bak/prompt_iter[N].bak`.

Spawn `meta-prompt-engineer` (use `file_read` to read its prompt.md as system prompt), all data sources read from files:

1. Use `file_read` to read `source/lyrics-golden-lines/prompt.md` (current Agent prompt)
2. Use `file_read` to read `source/lyrics-golden-lines/ideal_state.md` (ideal state description)
3. Use `file_read` to read `source/lyrics-golden-lines/changelog.md` (change history)
4. Use `file_read` to read `source/lyrics-golden-lines/tmp/iter_[N]/case_[i]_eval_result.md` (each evaluation result)
5. Use `file_read` to read `source/lyrics-golden-lines/testcases.yaml`, extract Inputs for cases scoring below 80

Assemble into Mode B `【】` format (structural illustration only — actual content read from files):

```
【当前 Agent 提示词】
[Read from prompt.md]

【理想态描述】
[Read from ideal_state.md]

【变更历史】
[Read from changelog.md]

【评估反馈】
[Extract each case's score and [prompt]-tagged issues and improvement suggestions from eval_result.md files]

【低分用例 Input】
[Read original Input text for cases scoring below 80 from testcases.yaml]
```

> ⚠️ **Never pass ExpectedOutput** — only pass Input and evaluation feedback. The prompt-engineer's rules explicitly prohibit access to ExpectedOutput.
>
> ⚠️ **Generalizability constraint**: The optimization goal is to improve the Agent's **general reasoning and generation capabilities**, not to make special adaptations for these 5 cases. All changes must be equally effective for inputs never seen before. No embedding few-shot examples similar to these 5 case themes in the prompt.
>
> ⚠️ **Filtering rule when passing evaluation feedback**: Among eval-judge's issue items, those tagged `[rubric]` or `[testcase]` **should not be passed to prompt-engineer** — those issues can't be solved by prompt changes. Only pass items tagged `[prompt]`.

🎉 **Extract the new prompt from the content after the `===PROMPT===` marker** — **hold as candidate prompt (don't write to prompt.md yet)**.

**4b-review. Spawn `meta-reviewer`** — Anti-cheat review (independent review before writing)

> 💡 This step is the key to the "generation and review separation" architecture — prompt-engineer generates, reviewer reviews, solving the "athlete judging themselves" problem.

1. Use `file_read` to read `source/meta-reviewer/prompt.md` as system prompt
2. Spawn sub agent, passing in:

```
【待审查提示词】
[Full text of candidate prompt from previous step's prompt-engineer output]

【测试用例】
[Read each case's Input and ExpectedOutput from testcases.yaml, listed one by one]

【审查上下文】
[This round's optimization changelog description]
```

3. Parse the review result after `===REVIEW_RESULT===` in the response:
   - **✅ PASS / ⚠️ WARN** → Candidate prompt passes review, use `file_write` to write to `source/lyrics-golden-lines/prompt.md`
   - **❌ REJECT** → Candidate prompt rejected, feed review findings (modification suggestions) back to prompt-engineer for re-optimization, retry up to 2 times
   - 3 consecutive REJECTs → Revert to backup prompt, record review blockage

Also append this round's optimization record to `source/lyrics-golden-lines/changelog.md`.

**4c. Display This Round's Changes (then immediately start next round — do not ask the user)**

Show the user:
- Score changes for each case (compared to previous round, can read from `tmp/iter_[N-1]/评估报告.md` and `tmp/iter_[N]/评估报告.md`)
- What changed in the prompt (summarize old/new prompt differences in plain language)
- Optimization direction for next round

> 🚨 **After displaying, immediately start the next round's 4a step automatically. Do not ask "should I continue?" or "proceed to next round?"**

**Repeat 4a–4c for 3 rounds.** After each round, display a progress table:

> ```
> 📊 Iteration Progress
>
> Round | Avg Score | Change | Key Improvement
> ------|-----------|--------|----------------
>   1   |  [score]  |   —    | [Read this round's improvement summary from changelog]
>   2   |  [score]  |  [Δ]   | [Read this round's improvement summary from changelog]
>   3   |  [score]  |  [Δ]   | [Read this round's improvement summary from changelog]
> ```

> 💡 **Context management tip**: Since artifacts are written to the file system, after each iteration the context only needs minimal information:
> - Current round number and previous round's average score (for progress tracking)
> - This round's evaluation summary (scores + `[prompt]`-tagged issues only, no full evaluation reports needed)
> - All other content (prompt, ideal state, Judge, ActualOutput, historical evaluation reports) can be read from files
>
> ⚠️ **Reiteration**: eval-judge may flag `[rubric]` or `[testcase]` in issue items, suggesting scoring criteria or reference answers may be problematic. **Ignore these suggestions** — do not modify any test case content. Test cases are fixed yardsticks — only the prompt can be changed.

### 🅱️🅲 CLI / IDE

> `iterate` is a multi-round loop task (each round: 5 tests + 5 evaluations + prompt optimization) — a single `-p` call would cause context explosion.
>
> **Solution**: Split into independent steps, each as a separate `-p` call. The benefit is that after each step, you can read artifacts and show the user exactly what changed.

### Iteration Round 1

**4.1 Back up the initial prompt** (needed for comparison later):
```bash
cp source/lyrics-golden-lines/prompt.md source/lyrics-golden-lines/bak/prompt_initial.bak
```

**4.2 Test + Evaluate + Generate Feedback**:
```bash
CodeBuddy --dangerously-skip-permissions -p "
test lyrics-golden-lines

After testing, please:
1. Summarize the evaluation report
2. Compile improvement notes and suggestions from each case into optimization recommendations
3. Save to source/lyrics-golden-lines/tmp/iter1_feedback.md
"
```

**4.3 Display This Round's Results**:
```bash
# See evaluation feedback — what needs improvement
cat source/lyrics-golden-lines/tmp/iter1_feedback.md
```

> 💡 **Display Tip**: Show scores + issues for each case one by one (read real data from `iter1_feedback.md`), e.g.: "[case theme] scored [X], because [specific issue identified by eval-judge]"

**4.4 Optimize the Prompt**:
```bash
CodeBuddy --dangerously-skip-permissions -p "
Read the following files:
- source/lyrics-golden-lines/prompt.md (current prompt)
- source/lyrics-golden-lines/ideal_state.md (ideal state)
- source/lyrics-golden-lines/changelog.md (change history)
- source/lyrics-golden-lines/tmp/iter1_feedback.md (evaluation feedback)

Please call meta-prompt-engineer to optimize the prompt.
Requirements: Make targeted improvements based on evaluation feedback issues, do not copy ExpectedOutput.
After optimization, first call meta-reviewer to review whether the prompt has cheating or overfitting:
- PASS / WARN → Write new prompt to source/lyrics-golden-lines/prompt.md
- REJECT → Feed review findings back to prompt-engineer for re-optimization (retry up to 2 times)
After review passes:
1. Append this round's optimization record to changelog.md (tag [Optimization])
2. Run ./venv/bin/python scripts/install.py lyrics-golden-lines to sync
"
```

**4.5 ⭐ See What Changed in the Prompt**:
```bash
# Compare initial version with optimized version
diff source/lyrics-golden-lines/bak/prompt_initial.bak source/lyrics-golden-lines/prompt.md

# See the changelog
cat source/lyrics-golden-lines/changelog.md
```

> 💡 **Display Tip**: Translate the diff into plain language for the user (content read from diff and changelog, do not fabricate):
>
> ```
> 📝 Round [N] Prompt Optimization:
>
> ✨ [Change 1 in plain language: summarize from diff]
> ✨ [Change 2 in plain language: summarize from diff]
> ✨ [Change 3 in plain language: summarize from diff]
> ```

### Iteration Rounds 2–3

**Repeat 4.2 – 4.5** (change `iter1` to `iter2`, `iter3`). After each round:

1. **Read the 5 new golden line responses** → Compare with previous round to see if Agent's golden lines improved
2. **Read the evaluation report** → See how much scores increased
3. **Read the diff** → See what changed in the prompt

```bash
# After round 2 testing, check the Agent's actual output again (best among 10 original candidates)
TEST_DIR=$(ls -td source/lyrics-golden-lines/tmp/test_* | head -1)
echo "===== 🎵 The Moon's Everyday Gentleness (watch score changes from last round) ====="
cat "$TEST_DIR/case_4_actual_result.txt"
```

> 💡 **Display Tip**: Visualize each round's progress (all data read from `评估报告.md` and `changelog.md`, do not fabricate):
>
> ```
> 📊 Iteration Progress
>
> Round | Avg Score | Change | Key Improvement
> ------|-----------|--------|----------------
>   1   |  [score]  |   —    | [Read from changelog]
>   2   |  [score]  |  [Δ]   | [Read from changelog]
>   3   |  [score]  |  [Δ]   | [Read from changelog]
>
> 🎵 Most improved case: [find case with largest score increase from evaluation reports]
>   Round 1: [read this case's performance from iter_1 evaluation report]
>   Round 3: [read this case's performance from iter_3 evaluation report]
> ```

### What Progress You'll See

Typically 3 rounds show significant improvement. The magnitude of improvement per round depends on the Agent and evaluation criteria, but the trend is consistent: scores rise each round, prompts evolve each round.

> 3 rounds are enough to experience the feeling of "AI self-evolution." Want to push higher? Repeat more rounds.

---

## Step 5: Compare Optimization Results — Full Panoramic Review

### 🅰️ OpenClaw

Use `file_read` to read historical artifacts from the file system and generate a panoramic comparison report:

1. Read `source/lyrics-golden-lines/bak/prompt_iter1.bak` (initial version)
2. Read `source/lyrics-golden-lines/prompt.md` (final version)
3. Read `source/lyrics-golden-lines/tmp/test_initial/评估报告.md` and `source/lyrics-golden-lines/tmp/iter_3/评估报告.md`
4. Read `source/lyrics-golden-lines/changelog.md`

Compare differences section by section, summarize score change trends, conclude key optimization strategies. Write the report to `source/lyrics-golden-lines/tmp/optimization_summary.md`.

### 🅱️🅲 CLI / IDE

```bash
CodeBuddy --dangerously-skip-permissions -p "
Please compare the before-and-after optimization results for lyrics-golden-lines:

1. Read source/lyrics-golden-lines/bak/prompt_initial.bak (initial version)
2. Read current source/lyrics-golden-lines/prompt.md (final version)
3. Compare differences section by section, explaining what problem each change solves
4. Extract score changes from each round in changelog.md
5. Conclusion: which optimization strategies improved scores the most, which were key turning points
6. Save the comparison report to source/lyrics-golden-lines/tmp/optimization_summary.md
"
```

Then read the report:
```bash
cat source/lyrics-golden-lines/tmp/optimization_summary.md
```

> 💡 **Display Tip**: This is the ultimate moment of satisfaction. Show with a comparison table (all data read from `bak/prompt_initial.bak`, `prompt.md`, both evaluation reports, and `changelog.md`, do not fabricate):
>
> ```
> 📊 Optimization Panorama
>
>                        Initial Version    →  Final Version
> ────────────────────────────────────────────────────────
> Average Score              [initial]           [final]
> Prompt Length              [initial words]     [final words]
> [Key dimension changes summarized from diff, e.g., whether reasoning chain or output format was added]
>
> 🎵 Most improved case: [find case with largest score increase from evaluation reports]
>    Initial: [read this case's performance from test_initial evaluation report]
>    Final: [read this case's performance from iter_3 evaluation report]
> ```
>
> **🎉 You set the standard (5 golden lines × 10 original candidates each), and AI figured out how to meet it. That's Meta-Agent.**

---

## 📋 Complete Workflow Quick Reference

### 🅰️ OpenClaw

| Step | Sub Agent Spawned | Input | Output (written to files) |
|------|-------------------|-------|--------------------------|
| 0 | — | — | Clone project locally |
| 1 | — | — | `demo_testcases.yaml` (written to file system) |
| 2 | `meta-prompt-engineer` → `meta-rubric-gen` × 5 | Ideal state + example cases | `prompt.md` + `ideal_state.md` + `testcases.yaml` |
| 3 | `lyrics-golden-lines` × 5 → `meta-eval-judge` × 5 | Input → evaluation | `tmp/test_initial/case_[N]_*.txt` + `评估报告.md` |
| 4 | Loop 3 rounds: Agent × 5 → Judge × 5 → Prompt Engineer → **Reviewer review** | Previous round feedback (read from files) | `tmp/iter_[N]/` + updated `prompt.md` + `changelog.md` |
| 5 | — | Read all history from files | `tmp/optimization_summary.md` |

### 🅱️🅲 CLI / IDE

| Step | Execute | What to Read After | What to Show |
|------|---------|-------------------|-------------|
| 0 | git clone + SETUP.md | verify_setup.py | Environment ✅ |
| 1 | Create demo_testcases.yaml | — | 5 golden-line test cases (10 original candidates each) |
| 2 | `-p "create agent ... method c"` | `prompt.md` + `ideal_state.md` | AI-written prompt and ideal state |
| 3 | `-p "test ..."` | `case_N_actual_result.txt` + evaluation report | **10 original candidate golden lines for each of 5 queries** + scores |
| 4 | Loop: test → feedback → optimize | `iter_feedback.md` + `diff` + `changelog.md` | Score changes per round + prompt modifications |
| 5 | `-p "compare bak/initial vs prompt.md"` | `optimization_summary.md` | Initial vs. final panoramic comparison |

> **Key**: The satisfaction comes not from "finished executing" but from **seeing what AI generated at each step** (files or conversation artifacts).

---

## ❓ FAQ

### Q: Why not use PTY interactive mode?

(CLI mode only) In PTY mode, the CLI's output is designed for human terminal viewing. The Agent receives a large chunk of stdout text, making it very hard to extract meaningful content for user display.

The **step-by-step `-p` + read files** approach is better:
1. Each step is an independent CLI call with clean context
2. Artifacts are saved as files (`.txt`, `.md`, `.yaml`) with clear structure
3. You can `cat` files and organize the display yourself

### Q: What's the difference between OpenClaw and CLI mode?

| Dimension | OpenClaw | CLI / IDE |
|-----------|---------|-----------|
| Installation | None required (project clone needed) | Requires CLI tool or IDE |
| File System | ✅ Supported (grant `file_read` / `file_write` / `list_directory` when spawning), artifacts written to `source/[Agent]/tmp/` | ✅ Supported (artifacts written to `source/[Agent]/tmp/`) |
| Tool Calling | File read/write + directory listing (granted via spawn `tools` parameter) | Full-featured (MCP, file read/write, command execution) |
| Shell Commands | ❌ Not supported | ✅ Supported |
| MCP Services | ❌ Not supported | ✅ Supported |
| Use Cases | Pure text-generation Agents (e.g., lyrics golden lines) | All Agents (including log analysis, code review, etc. requiring MCP) |
| Completeness | ⭐⭐⭐⭐⭐ (core workflow complete, artifacts persisted) | ⭐⭐⭐⭐⭐ (full features) |

### Q: Why split `iterate` into manual steps?

`iterate` is a multi-round loop: each round has 5 tests (each requiring 10 original candidate golden lines) + 5 evaluations + prompt optimization. A single `-p` call would cause context explosion.

Benefits of splitting into independent steps:
1. Clean context for each round
2. Can read files and show progress between rounds
3. Users can feel **each round's specific improvements** (more original golden lines, higher scores, what changed in the prompt)

### Q: Iterative optimization stuck at a score plateau?

First check if the evaluation criteria are reasonable:
```bash
CodeBuddy --dangerously-skip-permissions -p "calibrate lyrics-golden-lines"
```

### Q: What kinds of Agents can this project create?

**CLI / IDE mode**: Any "text input → text output" Agent, including those requiring tool calling: code review assistant, translation evaluation, customer service scripts, SQL assistant, log analysis, etc.

**OpenClaw mode**: Pure text-generation Agents + Agents involving file read/write. Original golden-line assistants, copywriting, translation refinement, code generation, etc. are all fine. Agents requiring MCP / shell command execution (like log analysis) should use CLI or IDE.

---

## 🧩 How It Works

```
Your 5 golden-line test cases (each requiring 10 original candidates)
    │
    ▼
meta-prompt-engineer ──→ Reverse-engineers a prompt from test cases
    │
    ▼
meta-rubric-gen ──→ Generates scoring criteria for each case (core: originality + imagery alignment + literary quality)
    │
    ▼
[Run Agent] ──→ Actual output (5 queries × 10 original candidate golden lines)
    │
    ▼
meta-eval-judge ──→ Scores each case + identifies shortcomings
    │
    ▼
meta-prompt-engineer ──→ Optimizes prompt based on shortcomings
    │
    ▼
meta-reviewer ──→ Independent review: cheating/overfitting? (✅ PASS → write / ❌ REJECT → redo)
    │                                              (loops ↑)
    ▼
meta-retrospective ──→ Global review every 3 rounds, preventing optimization drift
```

Core idea: **Use AI to solve AI's problems.** You set the standard, AI evolves itself.

---

## 🎓 Next Steps After Completion

1. **Create Your Own Agent** — Swap in different test cases, follow the same workflow
2. **Upgrade to CLI / IDE** — If you used OpenClaw, installing CLI tools unlocks MCP tool calling and shell command execution for more complex Agents (like log analysis)
3. **Deep-Dive into Evaluation** — `calibrate` to diagnose triplet consistency (CLI / IDE)
4. **Multi-Platform Testing** — `test lyrics-golden-lines on codebuddycli` (CLI / IDE)
5. **Read Full Documentation** — [README.md](README.md), [SETUP.md](SETUP.md)
