#!/usr/bin/env python3
"""
DSPy Prompt Optimizer — 基于 DSPy 的提示词优化器

用法:
    ./venv/bin/python scripts/dspy_optimizer.py --agent <agent_name> [options]

功能:
    1. 加载测试用例 (testcases.yaml) 作为 DSPy Dataset
    2. 使用 meta-eval-judge 作为 DSPy Metric
    3. 通过 DSPy Optimizer (BootstrapFewShot / MIPRO) 自动优化提示词
    4. 将优化后的提示词写回 prompt.md

流程:
    1. 读取 source/[agent]/testcases.yaml
    2. 转换为 DSPy Examples
    3. 定义 Agent Signature (从 ideal_state.md 推断)
    4. 调用 DSPy Optimizer 编译
    5. 提取优化后的 instructions 和 demonstrations
    6. 写入 prompt.md 和 changelog.md
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import dspy
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# Constants
# ============================================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")

# ============================================================================
# DSPy Signature Definition
# ============================================================================


class AgentSignature(dspy.Signature):
    """Generic Agent signature that adapts to task type."""

    input_text: str = dspy.InputField(desc="User input or query")
    output_text: str = dspy.OutputField(desc="Agent output or response")


# ============================================================================
# Agent Module
# ============================================================================


class AgentModule(dspy.Module):
    """Agent module that can be optimized by DSPy."""

    def __init__(self, agent_name: str, custom_instructions: str = ""):
        super().__init__()
        self.agent_name = agent_name
        self.custom_instructions = custom_instructions
        # Use ChainOfThought for better reasoning
        self.prog = dspy.ChainOfThought(AgentSignature)

    def forward(self, input_text: str):
        return self.prog(input_text=input_text)


# ============================================================================
# Dataset Loader
# ============================================================================


def load_testcases_as_examples(agent_dir: str) -> List[dspy.Example]:
    """
    Load test cases from testcases.yaml and convert to DSPy Examples.

    Args:
        agent_dir: Path to agent directory (e.g., source/meta-rubric-gen)

    Returns:
        List of DSPy Examples with 'input_text' and 'output_text' fields
    """
    yaml_path = os.path.join(agent_dir, "testcases.yaml")

    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"找不到测试用例文件: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    examples = []
    for i, case in enumerate(data.get("cases", [])):
        # Skip cases without Input or ExpectedOutput
        if not case.get("Input") or not case.get("ExpectedOutput"):
            print(f"⚠️  用例 {i+1} 缺少 Input 或 ExpectedOutput，跳过")
            continue

        example = dspy.Example(
            input_text=case["Input"],
            output_text=case["ExpectedOutput"],
        ).with_inputs("input_text")
        examples.append(example)

    print(f"✅ 加载了 {len(examples)} 条测试用例")
    return examples


# ============================================================================
# Metric Definition
# ============================================================================


def create_dspy_metric(agent_name: str, eval_threshold: float = 80.0):
    """
    Create a DSPy metric function that calls meta-eval-judge.

    This is a placeholder implementation. In production, this should:
    1. Call meta-eval-judge Sub Agent via Task tool
    2. Parse the evaluation score from the response
    3. Return True/False or a float score

    Args:
        agent_name: Name of the agent being optimized
        eval_threshold: Minimum score to consider as success

    Returns:
        Metric function compatible with DSPy
    """

    def metric(example: dspy.Example, pred: dspy.Prediction, trace=None) -> bool:
        """
        Evaluate prediction against expected output.

        In real implementation:
        1. Call meta-eval-judge with Input, ExpectedOutput, ActualOutput
        2. Parse score from response
        3. Return score >= threshold

        For now, use a simple string similarity metric.
        """
        # Placeholder: Simple keyword overlap
        expected = example.output_text.lower()
        actual = pred.output_text.lower()

        # Count common words (simple heuristic)
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        overlap = len(expected_words & actual_words)
        total = len(expected_words)

        if total == 0:
            return False

        similarity = overlap / total
        return similarity >= 0.7  # 70% word overlap as threshold

    return metric


# ============================================================================
# Optimizer Wrappers
# ============================================================================


def optimize_with_bootstrap(
    agent_module: AgentModule,
    trainset: List[dspy.Example],
    metric,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 16,
) -> dspy.Module:
    """
    Optimize agent using BootstrapFewShot.

    This optimizer automatically:
    1. Finds the best few-shot demonstrations from trainset
    2. Generates CoT reasoning chains for each demo
    3. Compiles them into the agent

    Args:
        agent_module: Agent module to optimize
        trainset: Training examples
        metric: Evaluation metric
        max_bootstrapped_demos: Max demos with generated reasoning
        max_labeled_demos: Max demos without reasoning

    Returns:
        Compiled agent with optimized demonstrations
    """
    from dspy.teleprompt import BootstrapFewShot

    print("🔧 使用 BootstrapFewShot 优化器...")
    print(f"   最大 Bootstrapped Demos: {max_bootstrapped_demos}")
    print(f"   最大 Labeled Demos: {max_labeled_demos}")

    teleprompter = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
    )

    compiled_agent = teleprompter.compile(agent_module, trainset=trainset)

    print("✅ BootstrapFewShot 优化完成")
    return compiled_agent


def optimize_with_mipro(
    agent_module: AgentModule,
    trainset: List[dspy.Example],
    metric,
    num_threads: int = 4,
    max_bootstrapped_demos: int = 4,
    num_trials: int = 10,
) -> dspy.Module:
    """
    Optimize agent using MIPRO (Multi-prompt Instruction Proposal Optimizer).

    This optimizer:
    1. Generates multiple instruction candidates
    2. Tries different combinations of instructions + demos
    3. Uses Bayesian optimization to find best combination

    Args:
        agent_module: Agent module to optimize
        trainset: Training examples
        metric: Evaluation metric
        num_threads: Parallel threads for evaluation
        max_bootstrapped_demos: Max few-shot demos
        num_trials: Number of optimization trials

    Returns:
        Compiled agent with optimized instructions and demos
    """
    try:
        from dspy.teleprompt import MIPROv2
    except ImportError:
        print("⚠️  MIPROv2 不可用，回退到 BootstrapFewShot")
        return optimize_with_bootstrap(agent_module, trainset, metric, max_bootstrapped_demos)

    print("🔧 使用 MIPRO 优化器...")
    print(f"   优化轮次: {num_trials}")
    print(f"   最大 Demos: {max_bootstrapped_demos}")

    teleprompter = MIPROv2(
        metric=metric,
        num_threads=num_threads,
        max_bootstrapped_demos=max_bootstrapped_demos,
        num_candidate_programs=10,
    )

    compiled_agent = teleprompter.compile(
        agent_module,
        trainset=trainset,
        num_trials=num_trials,
    )

    print("✅ MIPRO 优化完成")
    return compiled_agent


# ============================================================================
# Prompt Extraction
# ============================================================================


def extract_optimized_prompt(
    compiled_agent: dspy.Module,
    agent_name: str,
) -> Dict[str, Any]:
    """
    Extract instructions and demonstrations from compiled agent.

    Args:
        compiled_agent: Optimized DSPy module
        agent_name: Agent name for metadata

    Returns:
        Dict with 'instructions' and 'demonstrations' keys
    """
    result = {
        "agent_name": agent_name,
        "optimized_at": datetime.now().isoformat(),
        "instructions": "",
        "demonstrations": [],
    }

    # Extract from ChainOfThought module
    if hasattr(compiled_agent, "prog"):
        prog = compiled_agent.prog

        # Get instructions (if any)
        if hasattr(prog, "instructions"):
            result["instructions"] = prog.instructions

        # Get demonstrations
        if hasattr(prog, "demos"):
            for demo in prog.demos:
                demo_dict = {
                    "input": demo.input_text if hasattr(demo, "input_text") else str(demo),
                    "output": demo.output_text if hasattr(demo, "output_text") else "",
                }
                result["demonstrations"].append(demo_dict)

    print(f"✅ 提取了 {len(result['demonstrations'])} 个 Few-Shot 示例")
    return result


def format_as_prompt_md(extracted: Dict[str, Any], current_prompt: str) -> str:
    """
    Format extracted optimization results as prompt.md content.

    This function:
    1. Preserves the structure of current prompt.md
    2. Injects optimized instructions (if any)
    3. Injects optimized demonstrations as few-shot examples

    Args:
        extracted: Extracted instructions and demos
        current_prompt: Current prompt.md content

    Returns:
        New prompt.md content
    """
    # For now, return current prompt with DSPy optimization note
    # In production, this should intelligently merge the optimizations

    header = f"""# Optimized Prompt (DSPy)

> 🤖 本提示词由 DSPy 优化器自动生成
> 📅 优化时间: {extracted['optimized_at']}
> 📊 Few-Shot 示例数: {len(extracted['demonstrations'])}

"""

    # If we have new demonstrations, format them as few-shot section
    if extracted["demonstrations"]:
        few_shot_section = "\n## Few-Shot 示例 (DSPy 优化)\n\n"
        for i, demo in enumerate(extracted["demonstrations"], 1):
            few_shot_section += f"### 示例 {i}\n\n"
            few_shot_section += f"**输入:**\n{demo['input']}\n\n"
            few_shot_section += f"**输出:**\n{demo['output']}\n\n"
            few_shot_section += "---\n\n"

        # Insert before any existing "## 示例" section or at the end
        if "## 示例" in current_prompt:
            current_prompt = current_prompt.replace(
                "## 示例",
                few_shot_section + "\n## 示例",
                1,
            )
        else:
            current_prompt = current_prompt + "\n" + few_shot_section

    return current_prompt


# ============================================================================
# Main Optimizer Entry Point
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="DSPy Prompt Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 BootstrapFewShot 优化
  ./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen

  # 使用 MIPRO 优化（需要更多时间）
  ./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen --optimizer mipro

  # 指定 LLM 模型
  ./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen --model openai/gpt-4

  # Dry run (不写入文件)
  ./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen --dry-run
        """,
    )

    parser.add_argument("--agent", required=True, help="Agent 名称 (如 meta-rubric-gen)")
    parser.add_argument(
        "--optimizer",
        choices=["bootstrap", "mipro"],
        default="bootstrap",
        help="优化器类型 (默认: bootstrap)",
    )
    parser.add_argument("--model", default=None, help="LLM 模型 (如 openai/gpt-4)")
    parser.add_argument(
        "--max-demos",
        type=int,
        default=4,
        help="最大 Few-Shot 示例数 (默认: 4)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="评估分数阈值 (默认: 80.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅运行优化，不写入文件",
    )
    parser.add_argument(
        "--lm-api-key",
        default=None,
        help="LLM API Key (也可通过环境变量设置)",
    )
    parser.add_argument(
        "--lm-api-base",
        default=None,
        help="LLM API Base URL",
    )

    args = parser.parse_args()

    # =========================================================================
    # Setup
    # =========================================================================

    agent_name = args.agent
    agent_dir = os.path.join(SOURCE_DIR, agent_name)

    if not os.path.isdir(agent_dir):
        print(f"❌ 目录不存在: source/{agent_name}/")
        sys.exit(1)

    print("=" * 70)
    print(f"🚀 DSPy Prompt Optimizer")
    print("=" * 70)
    print(f"Agent: {agent_name}")
    print(f"优化器: {args.optimizer}")
    print(f"模型: {args.model or 'default'}")
    print(f"最大 Demos: {args.max_demos}")
    print(f"评估阈值: {args.threshold}")
    print("=" * 70)
    print()

    # =========================================================================
    # Configure DSPy LLM
    # =========================================================================

    # Determine model: command line arg > env var > default
    model_name = args.model or os.getenv("DSPY_MODEL") or "openai/gpt-4"
    api_key = args.lm_api_key or os.getenv("OPENAI_API_KEY")
    api_base = args.lm_api_base or os.getenv("OPENAI_BASE_URL")

    if not api_key:
        print("❌ 未找到 API Key。请在 .env 文件中配置 OPENAI_API_KEY，或通过参数传递。")
        sys.exit(1)

    print(f"🔧 配置 DSPy LLM: {model_name}")
    
    try:
        # Configure LLM for DSPy
        lm = dspy.LM(
            model=model_name,
            api_key=api_key,
            api_base=api_base,
        )
        dspy.settings.configure(lm=lm)
        print(f"✅ DSPy LLM 已配置\n")
    except Exception as e:
        print(f"❌ DSPy LLM 配置失败: {e}")
        sys.exit(1)

    # =========================================================================
    # Load Data
    # =========================================================================

    print("1️⃣ 加载测试用例...")
    examples = load_testcases_as_examples(agent_dir)

    if len(examples) == 0:
        print("❌ 没有可用的测试用例")
        sys.exit(1)

    # Split into train/dev (80/20)
    split_idx = int(len(examples) * 0.8)
    trainset = examples[:split_idx]
    devset = examples[split_idx:]

    print(f"   训练集: {len(trainset)} 条")
    print(f"   验证集: {len(devset)} 条\n")

    # =========================================================================
    # Initialize Agent Module
    # =========================================================================

    print("2️⃣ 初始化 Agent Module...")
    agent_module = AgentModule(agent_name)
    print("   ✅ 完成\n")

    # =========================================================================
    # Create Metric
    # =========================================================================

    print("3️⃣ 创建评估 Metric...")
    metric = create_dspy_metric(agent_name, args.threshold)
    print("   ✅ 完成\n")

    # =========================================================================
    # Optimize
    # =========================================================================

    print("4️⃣ 开始优化 (这可能需要几分钟)...")

    if args.optimizer == "mipro":
        compiled_agent = optimize_with_mipro(
            agent_module,
            trainset,
            metric,
            max_bootstrapped_demos=args.max_demos,
        )
    else:
        compiled_agent = optimize_with_bootstrap(
            agent_module,
            trainset,
            metric,
            max_bootstrapped_demos=args.max_demos,
        )

    print()

    # =========================================================================
    # Extract and Save Results
    # =========================================================================

    print("5️⃣ 提取优化结果...")
    extracted = extract_optimized_prompt(compiled_agent, agent_name)

    if args.dry_run:
        print("\n" + "=" * 70)
        print("🔍 DRY RUN 模式 - 不写入文件")
        print("=" * 70)
        print(json.dumps(extracted, ensure_ascii=False, indent=2))
        return

    # Load current prompt
    prompt_path = os.path.join(agent_dir, "prompt.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        current_prompt = f.read()

    # Format new prompt
    new_prompt = format_as_prompt_md(extracted, current_prompt)

    # Backup current prompt
    bak_dir = os.path.join(agent_dir, "bak")
    os.makedirs(bak_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = os.path.join(bak_dir, f"prompt_{timestamp}.bak")
    with open(bak_path, "w", encoding="utf-8") as f:
        f.write(current_prompt)
    print(f"   ✅ 备份已保存: {bak_path}")

    # Write new prompt
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(new_prompt)
    print(f"   ✅ 新提示词已保存: {prompt_path}")

    # Update changelog
    changelog_path = os.path.join(agent_dir, "changelog.md")
    changelog_entry = f"""
## [优化] DSPy 自动优化 (第 N 轮)

**优化时间:** {extracted['optimized_at']}
**优化器:** {args.optimizer}
**Few-Shot 示例数:** {len(extracted['demonstrations'])}
**训练集大小:** {len(trainset)}
**评估阈值:** {args.threshold}

**优化说明:**
- 使用 DSPy {args.optimizer} 优化器自动选择最佳 Few-Shot 示例
- 自动生成推理链 (Chain-of-Thought)
- 基于测试用例数据驱动优化

---

"""

    with open(changelog_path, "a", encoding="utf-8") as f:
        f.write(changelog_entry)
    print(f"   ✅ Changelog 已更新: {changelog_path}")

    print("\n" + "=" * 70)
    print("✅ DSPy 优化完成")
    print("=" * 70)
    print(f"下一步建议:")
    print(f"  1. 运行 test_agent {agent_name} 验证优化效果")
    print(f"  2. 如果满意，运行 ./venv/bin/python scripts/install.py {agent_name}")
    print(f"  3. 如果不满意，可从 bak/ 恢复旧版本")


if __name__ == "__main__":
    main()
