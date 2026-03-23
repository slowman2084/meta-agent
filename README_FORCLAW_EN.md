# Teach AI to Recommend Song Lyrics in 5 Minutes — Meta-Agent Quick Start

> **⏱️ Estimated Time**: Environment setup 5 min + Workflow experience 20–30 min (depending on execution method)
>
> You'll use 5 "pop song golden lines" test cases to experience the full Agent creation, testing, and iterative optimization workflow.
> 
> **OpenClaw Users**: No installation needed — complete the entire workflow right in your browser.

---

### 📖 Design Principles

**CLI / IDE Approach**: Each step is an independent CLI call (`-p` mode). After each step **completes**, read the generated files and showcase interesting content to the user.

**OpenClaw Approach**: Each step is completed via sub agent spawn. You (OpenClaw) read `source/meta-*/prompt.md` as the system prompt for each sub agent, passing intermediate artifacts (prompts, outputs, scores) through the conversation context — no file system needed.

The sense of achievement comes from "seeing what AI specifically wrote, what lyrics it recommended, how scores changed" — not just a "Done" message.

**Lyrics Evaluation Logic**: The Agent must generate **10 candidate golden lines** each time. Scoring primarily checks whether there is **at least 1 line achieving 90% similarity with ExpectedOutput** — this is the core scoring criterion.

---

## 🎯 What You'll Accomplish

```
5 song lyrics test cases (each requiring the Agent to recommend 10 candidate golden lines)
    → AI reverse-engineers a prompt (see how it understands "lyrics recommendation")
    → First test: see which 10 golden lines the Agent recommends for each query (actual content!)
    → 3 rounds of iterative optimization, each round showing prompt changes and score improvements
    → Final comparison: initial vs. final prompt, understanding AI's optimization strategy
```

---

## Prerequisites

### Choose Your Experience Mode

Meta-Agent supports three experience modes — pick **any one**:

| Mode | Installation Required | Best For | Completeness |
|------|----------------------|----------|-------------|
| **🅰️ OpenClaw** | None (browser only) | Quick exploration without setup | ⭐⭐⭐⭐ |
| **🅱️ AI IDE** | Cursor / CodeBuddy / Claude Code | Developers with existing IDEs | ⭐⭐⭐⭐⭐ |
| **🅲 CLI** | CodeBuddy CLI or Claude Code CLI | Terminal and scripting enthusiasts | ⭐⭐⭐⭐⭐ |

#### 🅰️ OpenClaw (Zero Barrier)

**No tools need to be installed.** OpenClaw calls Meta-Agent's sub agents (such as meta-prompt-engineer, meta-eval-judge, etc.) via sub agent spawn.

How it works:
- This document (`README_FORCLAW_EN.md`) itself is OpenClaw's execution handbook
- OpenClaw reads `source/meta-*/prompt.md` as the system prompt for each sub agent
- Completes the full **prompt generation → evaluation scoring → iterative optimization** workflow via sub agent spawn
- Orchestration rules are embedded in the step-by-step instructions in this document — no separate IDE installation needed
- Each sub agent has a specific input format (using `【】` format markers); this document provides exact templates at each step

> ⚠️ **Limitation**: Sub agents spawned by OpenClaw have no tool-calling capability (cannot read/write files or execute commands), so they're only suitable for **pure text-generation Agents** (like this demo's lyrics recommendation). Agents requiring MCP / tool calling (e.g., log analysis) still need CLI or IDE.

#### 🅱️ IDE Mode

Open the project directly in your IDE (Cursor / CodeBuddy / Claude Code) and type trigger words (e.g., `create_agent`) in the chat. The IDE automatically loads rules and sub agent configurations.

#### 🅲 CLI Mode

| CLI Tool | Installation | Notes |
|---------|-------------|-------|
| **CodeBuddy CLI** | Included with CodeBuddy IDE | Recommended, most complete experience |
| **Claude Code CLI** | `npm install -g @anthropic-ai/claude-code` | Requires Anthropic API Key |

---

## Step 0: Environment Setup

### 🅰️ OpenClaw

**No need to clone the project or set up any environment.** Jump directly to "Step 1" to prepare test cases.

OpenClaw needs to read the following 3 prompt files from the GitHub repository as system prompts when spawning sub agents:

| Sub Agent | GitHub Raw URL |
|-----------|---------------|
| Prompt Generation/Optimization Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-prompt-engineer/prompt.md` |
| Evaluation Scoring Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-eval-judge/prompt.md` |
| Scoring Criteria Generation Expert | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-rubric-gen/prompt.md` |

> 💡 If OpenClaw supports `web_fetch` or similar tools, you can read the above URLs directly. If not, you can manually paste the contents of these 3 files in the first conversation turn.

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

**No need to create files.** Keep the 5 test cases below in your conversation context — they'll be referenced directly in subsequent steps.

### 🅱️🅲 CLI / IDE

Create `demo_testcases.yaml` in the project root:

```yaml
meta:
  count: 5
  notice: "Pop song golden lines assistant demo — Agent must generate 10 candidate golden lines per query"
cases:
  - Input: |
      Generate 10 golden lyric lines based on "roller coaster ride"
    ExpectedOutput: |
      Baby our love is like a roller coaster ride, shooting me up to the sky then plummeting me down
      —— Mayday "Roller Coaster"
      (Above is a reference direction for the best among 10 lines; Agent output should contain 10 candidates)
    Judge: ""

  - Input: |
      Generate 10 golden lyric lines based on "what the world gave me"
    ExpectedOutput: |
      🎵 **The world gave me crickets chirping, and also gave me thunder; gave me a crescent moon, and also gave me evening stars**
      —— (Song name and artist to be filled by Agent)
      (Above is a reference direction for the best among 10 lines)
    Judge: ""

  - Input: |
      Generate 10 golden lyric lines about "every word is a secret crush"
    ExpectedOutput: |
      Every word of his never mentioned loving you, yet every sentence of yours says "I'm willing"
    Judge: ""

  - Input: |
      Generate 10 golden lyric lines about "a toast to myself"
    ExpectedOutput: |
      A toast to myself, from here on I won't look back
    Judge: ""

  - Input: |
      Are there any golden lyric lines about "the moon"? Please recommend 10.
    ExpectedOutput: |
      If the moon hasn't risen yet, the streetlamp can also light the windowsill
    Judge: ""
```

> 📝 **Core Scoring Logic**: The Agent must output **10 candidate golden lines**. The main scoring criterion in the Judge rubrics is: among the 10 lines, **at least 1 achieves 90% similarity with ExpectedOutput**. `Judge` is left empty — AI will auto-generate the corresponding rubrics later.

---

## Step 2: Create the Agent from Test Cases

### 🅰️ OpenClaw

Spawn 2 sub agents sequentially to complete creation:

**2a. Spawn `meta-prompt-engineer`** — Generate the prompt

Use the full content of `source/meta-prompt-engineer/prompt.md` as the system prompt, spawn a sub agent, and send the following user message (note the `【】` format markers — this is the required input format for this sub agent):

```
【理想态描述】
This Agent's function is: based on the user's mood, scenario, or keywords, recommend 10 matching pop song golden lyric lines, annotating song name and artist.
A good lyric recommendation Agent should:
- Accurately understand user intent (emotion, imagery, scenario)
- Consistently output 10 candidate golden lines per query
- Annotate each line with song name and artist
- Include at least 1 highly relevant match among candidates

【示例用例】
Input: Generate 10 golden lyric lines based on "roller coaster ride"
→ Best reference: Baby our love is like a roller coaster ride, shooting me up to the sky then plummeting me down —— Mayday "Roller Coaster"

Input: Generate 10 golden lyric lines based on "what the world gave me"
→ Best reference: The world gave me crickets chirping, and also gave me thunder; gave me a crescent moon, and also gave me evening stars

Input: Generate 10 golden lyric lines about "every word is a secret crush"
→ Best reference: Every word of his never mentioned loving you, yet every sentence of yours says "I'm willing"

Input: Generate 10 golden lyric lines about "a toast to myself"
→ Best reference: A toast to myself, from here on I won't look back

Input: Are there any golden lyric lines about "the moon"? Please recommend 10
→ Best reference: If the moon hasn't risen yet, the streetlamp can also light the windowsill
```

🎉 **Extract artifacts from the sub agent's response**:

The prompt-engineer's output contains an `===PROMPT===` marker — the content **after this marker** is the generated Agent prompt. Record it as `PROMPT` (used in subsequent steps).

Also, keep a copy of the ideal state description from the input as `IDEAL_STATE` — it will be passed to prompt-engineer during iterative optimization.

**2b. Spawn `meta-rubric-gen`** — Generate scoring criteria for each case

Use the full content of `source/meta-rubric-gen/prompt.md` as the system prompt, spawn **once per test case** (one case per spawn), passing in (using `【】` format markers):

```
【Input】
Generate 10 golden lyric lines based on "roller coaster ride"

【任务约束】
Core scoring logic: Agent must generate 10 candidate golden lines, with at least 1 achieving 90% similarity to the following reference line as the main scoring criterion.
Reference line: Baby our love is like a roller coaster ride, shooting me up to the sky then plummeting me down —— Mayday "Roller Coaster"
```

> Replace the Input and reference line for each test case accordingly. **No need to pass agent_name** (this demo has no references directory) — rubric-gen will generate scoring criteria directly based on Input content.

🎉 **Record 5 Judge scoring criteria** (YAML-format rubrics lists) for use in evaluation.

### 🅱️🅲 CLI / IDE

```bash
CodeBuddy --dangerously-skip-permissions -p "
Please execute the create_agent workflow:

1. Creation method: c (create from YAML test cases)
2. YAML file path: demo_testcases.yaml
3. Agent name: lyrics-golden-lines
4. Brief description: Based on user's mood or scenario, recommend 10 matching pop song golden lyric lines with song name and artist
5. Tool semantics: none (no tools needed)
6. MCP required: no
7. References: not needed, continue directly
8. Need additional test cases: no

Please follow the complete create_agent method c workflow, including: analyze cases to extract ideal state, call meta-prompt-engineer to generate prompt, call meta-rubric-gen to generate Judge for each case, run baseline model to fill ExpectedOutput, save to source/lyrics-golden-lines/testcases.yaml, run install.py to distribute.

Note: The core scoring logic for Judge is that the Agent must generate 10 candidate golden lines, with at least 1 achieving 90% similarity to ExpectedOutput as the main scoring criterion.
"
```

### 🎉 Creation Complete! (🅱️🅲 CLI / IDE) Read the generated files to see what AI did:

```bash
# 1. AI-written prompt — see how it understands "lyrics recommendation"
cat source/lyrics-golden-lines/prompt.md

# 2. AI-extracted ideal state — what it thinks a good lyric recommender should have
cat source/lyrics-golden-lines/ideal_state.md

# 3. AI-generated scoring criteria (Judge) for each case — see what dimensions it plans to score on
#    (use yaml_tool to read case 0's Judge field, avoiding reading the entire large YAML at once)
./venv/bin/python scripts/yaml_tool.py get source/lyrics-golden-lines/testcases.yaml 0 --fields Judge
```

> 💡 **Display Tip**: Show the core paragraphs of `prompt.md` to the user, letting them see "what recommendation logic AI derived from 5 golden lines." The Judge should show scoring dimensions like "generate 10 candidate lines" and "at least 1 with 90% similarity." This is the first moment of satisfaction.

---

## Step 3: First Test — See What the Agent Recommends

### 🅰️ OpenClaw

**3a. Spawn `lyrics-golden-lines`** — Get the Agent's actual output

Use the `PROMPT` generated in Step 2 as the system prompt, spawn a sub agent. Send the 5 Inputs **one by one** (just send the case content directly):

```
Generate 10 golden lyric lines based on "roller coaster ride"
```

Spawn separately for each case or send them sequentially within the same agent. Record 5 actual outputs (`ActualOutput_0` through `ActualOutput_4`).

**3b. Spawn `meta-eval-judge`** — Evaluate and score each case

Use the full content of `source/meta-eval-judge/prompt.md` as the system prompt, **spawn once per case** (never merge multiple cases), passing in (using `【】` format markers — this is the required input format for this sub agent):

```
【Input】
Generate 10 golden lyric lines based on "roller coaster ride"

【ExpectedOutput】
Baby our love is like a roller coaster ride, shooting me up to the sky then plummeting me down
—— Mayday "Roller Coaster"
(Above is a reference direction for the best among 10 lines; Agent output should contain 10 candidates)

【Judge】
[Paste the YAML rubrics generated in Step 2b for this case]

【ActualOutput】
[Paste the actual output from Step 3a for this case]
```

> Replace Input, ExpectedOutput, Judge, and ActualOutput for each case accordingly. eval-judge will score against each rubric criterion, outputting a total score and areas for improvement.

🎉 **Aggregate 5 scores** and calculate the average. Show the user each case's lyric recommendations and scores.

> 💡 **Display Tip**:
> ```
> 🎵 You asked: imagery of "roller coaster ride" (10 lines requested)
> 🤖 Agent recommended 10 lines, best match: "Baby our love is like a roller coaster ride…" —— Mayday "Roller Coaster"
> 📊 Score: 85/100 | Best match rate: 92% similarity ✅
> ```
>
> **A first-round score of 65–85 is normal. Remember this score — watch how AI evolves next.**

### 🅱️🅲 CLI / IDE

```bash
CodeBuddy --dangerously-skip-permissions -p "
test_agent lyrics-golden-lines
"
```

### 🎉 Test Complete! (🅱️🅲 CLI / IDE) Read results to see the Agent's specific outputs (10 candidate lines per case):

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
echo "===== 🎵 The Moon's Gentle Presence ====="
cat "$TEST_DIR/case_4_actual_result.txt"

# 📊 Evaluation report — score for each case and areas for improvement
cat "$TEST_DIR/评估报告.md"
```

> 💡 **Display Tip**:
> - Show the actual response for each of the 5 queries **one by one** — this is the most interesting part: "see what 10 lyric lines AI recommended for you"
> - Then show the score table from the evaluation report (core metric: whether at least 1 line achieves 90% similarity)
> - Organize the display like this:
>
> ```
> 🎵 You asked: imagery of "roller coaster ride" (10 lines requested)
> 🤖 Agent recommended 10 lines, best match: "Baby our love is like a roller coaster ride…" —— Mayday "Roller Coaster"
> 📊 Score: 85/100 | Best match rate: 92% similarity ✅
>
> 🎵 You asked: "the moon"'s gentle presence (10 lines requested)
> 🤖 Agent recommended 10 lines, but the closest match only reached 65% similarity
> 📊 Score: 62/100 | Issue: none of the 10 lines captured the "everyday gentleness" feel, leaning too grandiose
> ```
>
> **A first-round score of 65–85 is normal. Remember this score — watch how AI evolves next.**

---

## Step 4: Iterative Optimization — Watch AI Evolve

> Each iteration = Run Agent → Evaluate scores → Optimize prompt based on feedback. Repeat for 3 rounds and observe score changes.

### 🅰️ OpenClaw

Your conversation context holds: `PROMPT` (current prompt), `IDEAL_STATE` (ideal state), 5 Judges (YAML rubrics), and last round's scoring results.

**Each iteration involves 3 sub-steps:**

**4a. Run + Evaluate** (same as Step 3)

1. Use current `PROMPT` as system prompt, spawn `lyrics-golden-lines` sub agent, send 5 Inputs one by one, record 5 `ActualOutput`s
2. Use eval-judge's prompt.md as system prompt, spawn evaluation for each case (same `【】` format as Step 3b), get 5 scores and improvement notes

**4b. Optimize the Prompt**

Spawn `meta-prompt-engineer` (using its prompt.md as system prompt), passing in (using `【】` format markers — this is the standard input format for Mode B):

```
【当前 Agent 提示词】
[Paste the full current PROMPT]

【理想态描述】
[Paste IDEAL_STATE]

【评估反馈】
Case 1 (roller coaster ride): [score] points
Issues: [improvement notes from eval-judge]
Suggestions: [improvement suggestions from eval-judge]

Case 2 (what the world gave me): [score] points
Issues: [improvement notes]
Suggestions: [improvement suggestions]

...(all 5 cases)

【低分用例 Input】
[List the original Input text for cases scoring below 80]
```

> ⚠️ **Never pass ExpectedOutput** — only pass Input and evaluation feedback. The prompt-engineer's rules explicitly prohibit access to ExpectedOutput.

🎉 **Extract the new prompt from the content after the `===PROMPT===` marker** in the response, and replace `PROMPT` in your context.

**4c. Display This Round's Changes**

Show the user:
- Score changes for each case (compared to previous round)
- What changed in the prompt (summarize differences in plain language)
- Optimization direction for the next round

**Repeat 4a–4c for 3 rounds.** After each round, display a progress table:

> ```
> 📊 Iteration Progress
>
> Round | Avg Score | Change | Key Improvement
> ------|-----------|--------|----------------
>   1   |    72     |   —    | Initial version
>   2   |    83     |  +11   | Added reasoning chain
>   3   |    91     |   +8   | Added few-shot examples
> ```

> ⚠️ **Context Management Tip**: Each iteration involves 11 sub agent spawns (5 Agent + 5 Judge + 1 Prompt Engineer), totaling 33 across 3 rounds. After each round, keep only the following key artifacts for the next round's context, discarding spawn intermediate processes:
> - `PROMPT` (latest prompt)
> - `IDEAL_STATE` (ideal state, unchanged)
> - 5 Judges (unchanged)
> - This round's 5 score summaries (scores + issues only, no full evaluation reports needed)
> - 5 ExpectedOutputs (unchanged, needed for eval-judge parameters)

### 🅱️🅲 CLI / IDE

> `evo_looper` is a multi-round loop task (each round: 5 tests + 5 evaluations + prompt optimization) — a single `-p` call would cause context explosion.
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
test_agent lyrics-golden-lines

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

> 💡 **Display Tip**: Show scores + issues for each case, e.g.: "The moon's gentle presence scored only 69 because the Agent recommended overly grandiose lyrics, missing the 'everyday gentleness' requirement."

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
After optimization:
1. Write the new prompt to source/lyrics-golden-lines/prompt.md
2. Append this round's optimization record to changelog.md (tag [Optimization])
3. Run ./venv/bin/python scripts/install.py lyrics-golden-lines to sync
"
```

**4.5 ⭐ See What Changed in the Prompt**:
```bash
# Compare initial version with optimized version
diff source/lyrics-golden-lines/bak/prompt_initial.bak source/lyrics-golden-lines/prompt.md

# See the changelog
cat source/lyrics-golden-lines/changelog.md
```

> 💡 **Display Tip**: Translate the diff into plain language for the user, e.g.:
>
> ```
> 📝 Round 1 Prompt Optimization:
>
> ✨ Added "Reasoning Chain": Agent now first analyzes emotional keywords in the user's description
>    (e.g., "shooting up then plummeting" → thrilling ups and downs), then matches lyrics,
>    instead of searching for literal keywords.
>
> ✨ Added "Output Format Constraint": Requires unified format:
>    🎵 Golden Line —— "Song Name" Artist + one-line resonance interpretation.
>
> ✨ Added "Edge Case Handling": When user descriptions are vague (e.g., "everyday gentleness"),
>    Agent must first confirm understanding before recommending.
> ```

### Iteration Rounds 2–3

**Repeat 4.2 – 4.5** (change `iter1` to `iter2`, `iter3`). After each round:

1. **Read the 5 new lyric responses** → Compare with previous round to see if the Agent's answers improved
2. **Read the evaluation report** → See how much scores increased
3. **Read the diff** → See what changed in the prompt

```bash
# After round 2 testing, check the Agent's actual output again (best line among 10 candidates)
TEST_DIR=$(ls -td source/lyrics-golden-lines/tmp/test_* | head -1)
echo "===== 🎵 The Moon's Gentle Presence (last round: 62) ====="
cat "$TEST_DIR/case_4_actual_result.txt"
```

> 💡 **Display Tip**: Visualize each round's progress:
>
> ```
> 📊 Iteration Progress
>
> Round | Avg Score | Change | Key Improvement
> ------|-----------|--------|----------------
>   1   |    72     |   —    | Initial version, some cases had no hit among 10 lines
>   2   |    83     |  +11   | Added reasoning chain, "roller coaster" hit rate: 78%→95%
>   3   |    91     |   +8   | Added few-shot examples, "moon" finally has 1 line at 92% similarity
>
> 🎵 "The Moon's Gentle Presence" response evolution:
>   Round 1: All 10 lines too grandiose (highest similarity only 55%, score 62)
>   Round 3: Line #3 "If the moon hasn't risen yet, the streetlamp can also light the windowsill" reached 92% similarity (score 89)
> ```

### What Progress You'll See

Typically 3 rounds show significant improvement:

```
Iteration 1: Average 72
Iteration 2: Average 83  ↑11  ← Added reasoning chain/CoT, 10-line hit rate improved
Iteration 3: Average 91  ↑8   ← Added few-shot examples + edge case handling
```

> 3 rounds are enough to experience the feeling of "AI self-evolution." Want to push higher? Repeat more rounds.

---

## Step 5: Compare Optimization Results — Full Panoramic Review

### 🅰️ OpenClaw

Your conversation context already holds all history: initial prompt, optimized prompt from each round, and scores from each round. Generate a panoramic comparison report directly in the current conversation:

> Compare the initial prompt (version from Step 2) with the final prompt (version after Step 4, Round 3):
> 1. Compare differences section by section, explaining what problem each change solves
> 2. Summarize score change trends across all rounds
> 3. Conclusion: which optimization strategies improved scores the most, which were key turning points

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

> 💡 **Display Tip**: This is the ultimate moment of satisfaction. Show with a comparison table:
>
> ```
> 📊 Optimization Panorama
>
>                        Initial Version    →  Final Version
> ────────────────────────────────────────────────────────
> Average Score              72                  91
> Prompt Length              ~150 words          ~500 words
> Reasoning Chain (CoT)     ❌ None             ✅ Analyze emotion first → then match lyrics
> Output Format             ❌ Free-form         ✅ 10 candidates 🎵 Line —— "Song" Artist + interpretation
> Few-shot Examples         ❌ None             ✅ 2 high-quality demonstrations
>
> 🎵 Most improved case: "The Moon's Gentle Presence" 62 → 89 (+27 points)
>    Initial: All 10 lines too grandiose (highest similarity 55%)
>    Final: Line #3 "If the moon hasn't risen yet, the streetlamp can also light the windowsill" reached 92% similarity ✅
> ```
>
> **🎉 You set the standard (5 lyrics queries × 10 candidates each), and AI figured out how to meet it. That's Meta-Agent.**

---

## 📋 Complete Workflow Quick Reference

### 🅰️ OpenClaw

| Step | Sub Agent Spawned | Input | Output |
|------|-------------------|-------|--------|
| 0 | — | — | No setup needed |
| 1 | — | — | 5 test cases (stored in conversation context) |
| 2 | `meta-prompt-engineer` → `meta-rubric-gen` × 5 | Ideal state + example cases | Prompt `PROMPT` + 5 Judges |
| 3 | `lyrics-golden-lines` × 5 → `meta-eval-judge` × 5 | Input → evaluation | 5 lyric outputs + 5 scores |
| 4 | Loop 3 rounds: Agent × 5 → Judge × 5 → Prompt Engineer | Previous round feedback | Score changes per round + new prompt |
| 5 | — | All history in conversation context | Initial vs. final panoramic comparison |

### 🅱️🅲 CLI / IDE

| Step | Execute | What to Read After | What to Show |
|------|---------|-------------------|-------------|
| 0 | git clone + SETUP.md | verify_setup.py | Environment ✅ |
| 1 | Create demo_testcases.yaml | — | 5 lyrics test cases (10 candidates each) |
| 2 | `-p "create_agent ... method c"` | `prompt.md` + `ideal_state.md` | AI-written prompt and ideal state |
| 3 | `-p "test_agent ..."` | `case_N_actual_result.txt` + evaluation report | **10 candidate lines for each of 5 queries** + scores |
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
| Installation | None required | Requires CLI tool or IDE |
| File System | None (all intermediate artifacts stored in conversation context) | Yes (artifacts written to `source/[Agent]/tmp/`) |
| Tool Calling | Not supported (pure text sub agents) | Supported (MCP, file read/write, command execution) |
| Use Cases | Pure text-generation Agents (e.g., lyrics recommendation) | All Agents (including log analysis, code review, etc. requiring tools) |
| Completeness | ⭐⭐⭐⭐ (core workflow complete) | ⭐⭐⭐⭐⭐ (full features) |

### Q: Why split `evo_looper` into manual steps?

`evo_looper` is a multi-round loop: each round has 5 tests (10 candidate lines each) + 5 evaluations + prompt optimization. A single `-p` call would cause context explosion.

Benefits of splitting into independent steps:
1. Clean context for each round
2. Can read files and show progress between rounds
3. Users can feel **each round's specific improvements** (better lyric responses, higher scores, what changed in the prompt)

### Q: Iterative optimization stuck at a score plateau?

First check if the evaluation criteria are reasonable:
```bash
CodeBuddy --dangerously-skip-permissions -p "calibrate lyrics-golden-lines"
```

### Q: What kinds of Agents can this project create?

**CLI / IDE mode**: Any "text input → text output" Agent, including those requiring tool calling: code review assistant, translation evaluation, customer service scripts, SQL assistant, log analysis, etc.

**OpenClaw mode**: Limited to pure text-generation Agents (no tool calling). Lyric recommendation, copywriting, translation refinement, etc. are all fine. Agents requiring MCP / file operations / command execution should use CLI or IDE.

---

## 🧩 How It Works

```
Your 5 lyric test cases (each requesting 10 candidates)
    │
    ▼
meta-prompt-engineer ──→ Reverse-engineers a prompt from test cases
    │
    ▼
meta-rubric-gen ──→ Generates scoring criteria for each case (core: at least 1 of 10 lines at 90% similarity)
    │
    ▼
[Run Agent] ──→ Actual output (5 queries × 10 candidate golden lines)
    │
    ▼
meta-eval-judge ──→ Scores each case + identifies shortcomings
    │
    ▼
meta-prompt-engineer ──→ Optimizes prompt based on shortcomings (loops ↑)
    │
    ▼
meta-retrospective ──→ Global review every 3 rounds, preventing optimization drift
```

Core idea: **Use AI to solve AI's problems.** You set the standard, AI evolves itself.

---

## 🎓 Next Steps After Completion

1. **Create Your Own Agent** — Swap in different test cases, follow the same workflow
2. **Upgrade to CLI / IDE** — If you used OpenClaw, installing CLI tools unlocks tool-calling capabilities for more complex Agents
3. **Deep-Dive into Evaluation** — `calibrate` to diagnose triplet consistency (CLI / IDE)
4. **Multi-Platform Testing** — `test_agent lyrics-golden-lines@codebuddycli` (CLI / IDE)
5. **Read Full Documentation** — [README.md](README.md), [SETUP.md](SETUP.md)
