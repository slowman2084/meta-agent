#!/usr/bin/env python3
"""
Setup Verification Script — Verify meta-agent project initialization status.

Usage:
    ./venv/bin/python scripts/verify_setup.py           # Full verification
    ./venv/bin/python scripts/verify_setup.py --json    # JSON output for AI parsing
    ./venv/bin/python scripts/verify_setup.py --fix     # Attempt auto-fix for some issues

Exit codes:
    0 - All checks passed
    1 - Some checks failed (see output for details)
"""

import argparse
import json
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_venv():
    """Check if virtual environment exists."""
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
    exists = os.path.isfile(venv_python)
    return {
        "name": "Virtual Environment",
        "status": "pass" if exists else "fail",
        "message": "venv/bin/python exists" if exists else "venv not found",
        "fix_command": "python3 -m venv venv" if not exists else None,
    }


def check_dependencies():
    """Check if Python dependencies are installed."""
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
    if not os.path.isfile(venv_python):
        return {
            "name": "Python Dependencies",
            "status": "skip",
            "message": "Skipped (venv not found)",
            "fix_command": None,
        }

    try:
        result = subprocess.run(
            [venv_python, "-c", "import langchain_core; import langgraph; import mcp"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {
                "name": "Python Dependencies",
                "status": "pass",
                "message": "Core dependencies (langchain, langgraph, mcp) OK",
                "fix_command": None,
            }
        else:
            return {
                "name": "Python Dependencies",
                "status": "fail",
                "message": f"Import error: {result.stderr.strip()[:100]}",
                "fix_command": "./venv/bin/pip install -r requirements.txt",
            }
    except Exception as e:
        return {
            "name": "Python Dependencies",
            "status": "fail",
            "message": f"Check failed: {str(e)[:100]}",
            "fix_command": "./venv/bin/pip install -r requirements.txt",
        }


def check_mcp_config():
    """Check if MCP configuration exists."""
    mcp_json = os.path.join(PROJECT_ROOT, ".mcp.json")
    mcp_example = os.path.join(PROJECT_ROOT, ".mcp.json.example")

    if os.path.isfile(mcp_json):
        # Check if it has real values (not placeholders)
        try:
            with open(mcp_json, "r") as f:
                content = f.read()
            if "<your-secret-id>" in content or "<your-secret-key>" in content:
                return {
                    "name": "MCP Configuration",
                    "status": "warn",
                    "message": ".mcp.json exists but contains placeholder values",
                    "fix_command": "Edit .mcp.json and replace placeholder values",
                }
            return {
                "name": "MCP Configuration",
                "status": "pass",
                "message": ".mcp.json configured",
                "fix_command": None,
            }
        except Exception:
            return {
                "name": "MCP Configuration",
                "status": "warn",
                "message": ".mcp.json exists but could not be read",
                "fix_command": None,
            }
    elif os.path.isfile(mcp_example):
        return {
            "name": "MCP Configuration",
            "status": "warn",
            "message": ".mcp.json not found (optional, template available)",
            "fix_command": "cp .mcp.json.example .mcp.json && edit .mcp.json",
        }
    else:
        return {
            "name": "MCP Configuration",
            "status": "warn",
            "message": ".mcp.json not found (optional)",
            "fix_command": None,
        }


def check_source_directory():
    """Check if source directory has agents."""
    source_dir = os.path.join(PROJECT_ROOT, "source")
    if not os.path.isdir(source_dir):
        return {
            "name": "Source Directory",
            "status": "fail",
            "message": "source/ directory not found",
            "fix_command": "mkdir source",
        }

    agents = [
        d
        for d in os.listdir(source_dir)
        if os.path.isdir(os.path.join(source_dir, d)) and not d.startswith(".")
    ]

    if agents:
        return {
            "name": "Source Directory",
            "status": "pass",
            "message": f"Found {len(agents)} agent(s): {', '.join(agents[:5])}{'...' if len(agents) > 5 else ''}",
            "fix_command": None,
        }
    else:
        return {
            "name": "Source Directory",
            "status": "warn",
            "message": "source/ exists but no agents found",
            "fix_command": "./venv/bin/python scripts/scaffold.py <AgentName>",
        }


def check_scripts():
    """Check if core scripts exist."""
    required_scripts = ["install.py", "scaffold.py"]
    scripts_dir = os.path.join(PROJECT_ROOT, "scripts")

    missing = []
    for script in required_scripts:
        if not os.path.isfile(os.path.join(scripts_dir, script)):
            missing.append(script)

    if not missing:
        return {
            "name": "Core Scripts",
            "status": "pass",
            "message": "install.py, scaffold.py found",
            "fix_command": None,
        }
    else:
        return {
            "name": "Core Scripts",
            "status": "fail",
            "message": f"Missing: {', '.join(missing)}",
            "fix_command": None,
        }


def check_ide_directories():
    """Check if IDE agent directories exist."""
    ide_dirs = [".cursor/agents", ".codebuddy/agents", ".claude/agents"]
    existing = []
    missing = []

    for ide_dir in ide_dirs:
        full_path = os.path.join(PROJECT_ROOT, ide_dir)
        if os.path.isdir(full_path):
            existing.append(ide_dir.split("/")[0])
        else:
            missing.append(ide_dir.split("/")[0])

    if not missing:
        return {
            "name": "IDE Directories",
            "status": "pass",
            "message": f"All IDE directories exist ({', '.join(existing)})",
            "fix_command": None,
        }
    elif existing:
        return {
            "name": "IDE Directories",
            "status": "warn",
            "message": f"Some missing: {', '.join(missing)}",
            "fix_command": "./venv/bin/python scripts/install.py",
        }
    else:
        return {
            "name": "IDE Directories",
            "status": "warn",
            "message": "No IDE directories found (run install.py to create)",
            "fix_command": "./venv/bin/python scripts/install.py",
        }


def check_rules_installed():
    """Check if rules are installed to IDE directories."""
    source_rules = os.path.join(PROJECT_ROOT, "source", "rules")
    if not os.path.isdir(source_rules):
        return {
            "name": "Rules Installation",
            "status": "warn",
            "message": "source/rules/ not found",
            "fix_command": None,
        }

    rule_files = [f for f in os.listdir(source_rules) if f.endswith(".mdc")]
    if not rule_files:
        return {
            "name": "Rules Installation",
            "status": "warn",
            "message": "No .mdc files in source/rules/",
            "fix_command": None,
        }

    ide_rules_dirs = [".cursor/rules", ".codebuddy/rules", ".claude/rules"]
    missing_dirs = []
    missing_files = []

    for ide_dir in ide_rules_dirs:
        full_dir = os.path.join(PROJECT_ROOT, ide_dir)
        if not os.path.isdir(full_dir):
            missing_dirs.append(ide_dir)
            continue
        for rf in rule_files:
            if not os.path.isfile(os.path.join(full_dir, rf)):
                missing_files.append(f"{ide_dir}/{rf}")

    if not missing_dirs and not missing_files:
        return {
            "name": "Rules Installation",
            "status": "pass",
            "message": f"{len(rule_files)} rule(s) installed to all IDE directories",
            "fix_command": None,
        }
    else:
        detail = []
        if missing_dirs:
            detail.append(f"missing dirs: {', '.join(missing_dirs)}")
        if missing_files:
            detail.append(f"missing files: {', '.join(missing_files[:3])}{'...' if len(missing_files) > 3 else ''}")
        return {
            "name": "Rules Installation",
            "status": "warn",
            "message": f"Rules not fully installed ({'; '.join(detail)})",
            "fix_command": "./venv/bin/python scripts/install.py --rules-only",
        }


def check_requirements_file():
    """Check if requirements.txt exists."""
    req_file = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.isfile(req_file):
        return {
            "name": "Requirements File",
            "status": "pass",
            "message": "requirements.txt found",
            "fix_command": None,
        }
    else:
        return {
            "name": "Requirements File",
            "status": "fail",
            "message": "requirements.txt not found",
            "fix_command": None,
        }


def run_all_checks():
    """Run all verification checks."""
    checks = [
        check_venv,
        check_requirements_file,
        check_dependencies,
        check_mcp_config,
        check_source_directory,
        check_scripts,
        check_ide_directories,
        check_rules_installed,
    ]

    results = []
    for check_fn in checks:
        try:
            result = check_fn()
            results.append(result)
        except Exception as e:
            results.append(
                {
                    "name": check_fn.__name__,
                    "status": "error",
                    "message": f"Check failed: {str(e)[:100]}",
                    "fix_command": None,
                }
            )

    return results


def print_results(results, json_output=False):
    """Print verification results."""
    if json_output:
        output = {
            "results": results,
            "summary": {
                "total": len(results),
                "pass": sum(1 for r in results if r["status"] == "pass"),
                "fail": sum(1 for r in results if r["status"] == "fail"),
                "warn": sum(1 for r in results if r["status"] == "warn"),
                "skip": sum(1 for r in results if r["status"] == "skip"),
            },
        }
        output["summary"]["all_pass"] = output["summary"]["fail"] == 0
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return output["summary"]["all_pass"]

    # Human-readable output
    print("=" * 60)
    print("Meta-Agent Setup Verification")
    print("=" * 60)
    print()

    status_icons = {
        "pass": "✅",
        "fail": "❌",
        "warn": "⚠️ ",
        "skip": "⏭️ ",
        "error": "💥",
    }

    for result in results:
        icon = status_icons.get(result["status"], "❓")
        print(f"{icon} {result['name']}: {result['message']}")
        if result.get("fix_command") and result["status"] in ("fail", "warn"):
            print(f"   Fix: {result['fix_command']}")

    print()
    print("-" * 60)

    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    warn_count = sum(1 for r in results if r["status"] == "warn")

    if fail_count == 0:
        print(f"✅ All critical checks passed ({pass_count} pass, {warn_count} warnings)")
        return True
    else:
        print(f"❌ {fail_count} check(s) failed ({pass_count} pass, {warn_count} warnings)")
        return False


def attempt_fixes(results):
    """Attempt to auto-fix some issues."""
    print("Attempting auto-fixes...\n")

    fixed = 0
    for result in results:
        if result["status"] == "fail" and result.get("fix_command"):
            cmd = result["fix_command"]
            # Only auto-fix safe commands
            safe_prefixes = ["mkdir", "python3 -m venv", "./venv/bin/pip install"]
            if any(cmd.startswith(prefix) for prefix in safe_prefixes):
                print(f"Running: {cmd}")
                try:
                    os.chdir(PROJECT_ROOT)
                    subprocess.run(cmd, shell=True, check=True)
                    print(f"  ✅ Fixed: {result['name']}\n")
                    fixed += 1
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ Failed: {e}\n")
            else:
                print(f"⏭️  Skipping (requires manual action): {cmd}\n")

    return fixed


def main():
    parser = argparse.ArgumentParser(
        description="Verify meta-agent project setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-fix some issues",
    )
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    results = run_all_checks()

    if args.fix:
        attempt_fixes(results)
        # Re-run checks after fixes
        results = run_all_checks()

    all_pass = print_results(results, json_output=args.json)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
