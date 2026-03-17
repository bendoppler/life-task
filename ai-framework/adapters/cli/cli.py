#!/usr/bin/env python3
"""
AI Agent Framework CLI

Orchestrates the multi-agent TDD workflow for Swift monorepo development.
Supports Claude API and Ollama backends.

Usage:
    python cli.py --backend claude --feature "Add a TaskList feature"
    python cli.py --backend ollama --feature "Add a TaskList feature"
    python cli.py --backend ollama --model qwen2.5-coder:32b --feature "Add a TaskList feature"
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml


AGENTS = ["secretary", "architecture", "unit-test", "code", "ui-test"]
DIFF_LIMIT = 500


def get_project_root() -> Path:
    """Find the project root (directory containing ai-framework/)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "ai-framework").is_dir():
            return current
        current = current.parent
    sys.exit("Could not find project root (no ai-framework/ directory found)")


def load_prompt(agent_name: str, project_root: Path) -> str:
    """Load a prompt template from ai-framework/prompts/."""
    prompt_path = project_root / "ai-framework" / "prompts" / f"{agent_name}.md"
    if not prompt_path.exists():
        sys.exit(f"Prompt not found: {prompt_path}")
    return prompt_path.read_text()


def load_contract(agent_name: str, project_root: Path) -> str:
    """Load a contract from ai-framework/contracts/."""
    contract_path = project_root / "ai-framework" / "contracts" / f"{agent_name}-contract.md"
    if contract_path.exists():
        return contract_path.read_text()
    return ""


def read_file_if_exists(path: Path) -> str:
    """Read a file's contents if it exists, otherwise return empty string."""
    if path.exists():
        return path.read_text()
    return ""


def get_diff_size(project_root: Path) -> int:
    """Get the total insertions + deletions from git diff."""
    result = subprocess.run(
        ["git", "diff", "--stat"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    last_line = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
    insertions = 0
    deletions = 0
    if "insertion" in last_line:
        parts = last_line.split(",")
        for part in parts:
            part = part.strip()
            if "insertion" in part:
                insertions = int(part.split()[0])
            elif "deletion" in part:
                deletions = int(part.split()[0])
    return insertions + deletions


def check_diff_gate(project_root: Path, feature_name: str) -> bool:
    """Check if diff exceeds 500 lines. Returns True if we should stop and PR."""
    diff_size = get_diff_size(project_root)
    print(f"  Diff size: {diff_size}/{DIFF_LIMIT} lines")
    if diff_size >= DIFF_LIMIT:
        print(f"  ⚠ Diff exceeds {DIFF_LIMIT} lines. Creating PR and restarting.")
        subprocess.run(["git", "add", "-A"], cwd=project_root)
        subprocess.run(
            ["git", "commit", "-m", f"feat({feature_name}): partial implementation"],
            cwd=project_root,
        )
        subprocess.run(
            ["gh", "pr", "create", "--title", f"feat({feature_name}): partial", "--body", "Auto-created by AI framework (500-line limit reached)"],
            cwd=project_root,
        )
        return True
    return False


def invoke_agent(backend: str, prompt: str, model: str | None = None) -> str:
    """Invoke an AI agent with the given prompt using the specified backend."""
    if backend == "claude":
        from backends.claude import invoke
        kwargs = {"prompt": prompt}
        if model:
            kwargs["model"] = model
        return invoke(**kwargs)
    elif backend == "ollama":
        from backends.ollama import invoke
        kwargs = {"prompt": prompt}
        if model:
            kwargs["model"] = model
        return invoke(**kwargs)
    else:
        sys.exit(f"Unknown backend: {backend}")


def inject_variables(template: str, variables: dict[str, str]) -> str:
    """Replace {{VARIABLE}} placeholders in a template."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


LAYERS = ["domain", "data", "presentation", "view"]


def run_secretary(backend: str, project_root: Path, model: str | None) -> str:
    """Invoke Secretary AI and return project status."""
    status_path = project_root / "ai-framework" / "PROJECT_STATUS.md"
    previous_status = read_file_if_exists(status_path)

    if previous_status:
        print("Secretary AI — Incremental update (previous status found)...")
    else:
        print("Secretary AI — Full scan (no previous status)...")

    secretary_prompt = load_prompt("secretary", project_root)
    secretary_prompt = inject_variables(secretary_prompt, {
        "PROJECT_ROOT": str(project_root),
        "PREVIOUS_STATUS": previous_status,
        "TIMESTAMP": subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
    })
    secretary_output = invoke_agent(backend, secretary_prompt, model)
    status_path.write_text(secretary_output)
    print(f"  Written: {status_path}")
    return status_path.read_text()


def run_layer_cycle(
    backend: str,
    project_root: Path,
    feature: str,
    model: str | None,
    layer: str,
    project_status: str,
    arch_output: str,
) -> tuple[str, str]:
    """Run a single layer cycle: Unit Test → Code → diff gate. Returns (ut_output, code_output)."""
    ut_conventions = read_file_if_exists(project_root / "CDM-How to write unit tests.md")

    if layer != "view":
        print(f"  Unit Test AI — Writing {layer} layer tests...")
        ut_prompt = load_prompt("unit-test", project_root)
        ut_contract = load_contract("unit-test", project_root)
        ut_prompt = inject_variables(ut_prompt + "\n\n" + ut_contract, {
            "FEATURE_REQUEST": feature,
            "PROJECT_STATUS": project_status,
            "PROTOCOL_FILES": arch_output,
            "UNIT_TEST_CONVENTIONS": ut_conventions,
            "CURRENT_LAYER": layer,
        })
        ut_output = invoke_agent(backend, ut_prompt, model)
        print(ut_output[:200] + "..." if len(ut_output) > 200 else ut_output)
    else:
        ut_output = ""

    print(f"  Code AI — Implementing {layer} layer...")
    code_prompt = load_prompt("code", project_root)
    code_contract = load_contract("code", project_root)
    code_prompt = inject_variables(code_prompt + "\n\n" + code_contract, {
        "FEATURE_REQUEST": feature,
        "PROJECT_STATUS": project_status,
        "PROTOCOL_FILES": arch_output,
        "UNIT_TEST_FILES": ut_output,
        "CURRENT_LAYER": layer,
    })
    code_output = invoke_agent(backend, code_prompt, model)
    print(code_output[:200] + "..." if len(code_output) > 200 else code_output)

    return ut_output, code_output


def run_workflow(backend: str, feature: str, model: str | None = None):
    """Run the full orchestrator workflow with bottom-up layer cycles."""
    project_root = get_project_root()
    print(f"Project root: {project_root}")
    print(f"Backend: {backend}")
    print(f"Feature: {feature}")
    print()

    # Secretary
    print("=" * 60)
    print("Phase 1: Secretary + Architecture")
    print("=" * 60)
    project_status = run_secretary(backend, project_root, model)
    print()

    # Architecture (runs once)
    print("Architecture AI — Planning package structure + layer decomposition...")
    arch_prompt = load_prompt("architecture", project_root)
    arch_contract = load_contract("architecture", project_root)
    arch_prompt = inject_variables(arch_prompt + "\n\n" + arch_contract, {
        "FEATURE_REQUEST": feature,
        "PROJECT_STATUS": project_status,
        "PROJECT_ROOT": str(project_root),
    })
    arch_output = invoke_agent(backend, arch_prompt, model)
    print(arch_output)
    print()

    if check_diff_gate(project_root, feature):
        print("Restarting from new base after architecture...")
        project_status = run_secretary(backend, project_root, model)

    # Layer cycles: Domain → Data → Presentation → View
    all_code_output = ""
    all_ut_output = ""

    for i, layer in enumerate(LAYERS):
        cycle_num = i + 1
        print("=" * 60)
        print(f"Cycle {cycle_num}: {layer.title()} Layer")
        print("=" * 60)

        if cycle_num > 1:
            project_status = run_secretary(backend, project_root, model)

        ut_output, code_output = run_layer_cycle(
            backend, project_root, feature, model,
            layer, project_status, arch_output,
        )
        all_ut_output += ut_output
        all_code_output += code_output

        if layer == "view":
            print("  UI Test AI — Writing UI tests...")
            ui_prompt = load_prompt("ui-test", project_root)
            ui_contract = load_contract("ui-test", project_root)
            ui_prompt = inject_variables(ui_prompt + "\n\n" + ui_contract, {
                "FEATURE_REQUEST": feature,
                "PROJECT_STATUS": project_status,
                "PROTOCOL_FILES": arch_output,
                "PRODUCTION_CODE": all_code_output,
                "UNIT_TEST_FILES": all_ut_output,
                "UI_TEST_CONVENTIONS": "",
            })
            ui_output = invoke_agent(backend, ui_prompt, model)
            print(ui_output[:200] + "..." if len(ui_output) > 200 else ui_output)

        if check_diff_gate(project_root, feature):
            print(f"  PR created after {layer} layer. Continuing to next cycle...")
            continue

        print()

    print("=" * 60)
    print("Workflow complete.")
    print("=" * 60)
    diff_size = get_diff_size(project_root)
    print(f"Total diff: {diff_size} lines")
    print("Review the changes and commit when ready.")


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Framework CLI for Swift TDD development"
    )
    parser.add_argument(
        "--backend",
        choices=["claude", "ollama"],
        required=True,
        help="AI backend to use",
    )
    parser.add_argument(
        "--feature",
        required=True,
        help="Feature request description",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model override (e.g., claude-sonnet-4-20250514, qwen2.5-coder:32b)",
    )
    args = parser.parse_args()

    run_workflow(args.backend, args.feature, args.model)


if __name__ == "__main__":
    main()
