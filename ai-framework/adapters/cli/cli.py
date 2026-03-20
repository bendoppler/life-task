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

from parser import parse_output, write_files, execute_actions


AGENTS = ["secretary", "architecture", "unit-test", "code", "ui-test"]
DIFF_LIMIT = 500
MAX_RETRIES = 3


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


def load_output_format(project_root: Path) -> str:
    """Load the structured output format reference."""
    path = project_root / "ai-framework" / "references" / "output-format.md"
    if path.exists():
        return path.read_text()
    return ""


def read_file_if_exists(path: Path) -> str:
    """Read a file's contents if it exists, otherwise return empty string."""
    if path.exists():
        return path.read_text()
    return ""


def get_diff_size(project_root: Path) -> int:
    """Get the total insertions + deletions from git diff HEAD."""
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
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


def invoke_agent(
    backend: str,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int = 16384,
) -> str:
    """Invoke an AI agent with separate system and user prompts."""
    if backend == "claude":
        from backends.claude import invoke
        return invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
        )
    elif backend == "ollama":
        from backends.ollama import invoke
        # Ollama doesn't support system prompts natively in generate API,
        # so concatenate them
        combined = system_prompt + "\n\n---\n\n" + user_prompt
        kwargs = {"prompt": combined}
        if model:
            kwargs["model"] = model
        return invoke(**kwargs)
    else:
        sys.exit(f"Unknown backend: {backend}")


def invoke_agent_with_retry(
    backend: str,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int = 16384,
    error_context: str = "",
) -> str:
    """Invoke an agent with retry logic (up to MAX_RETRIES attempts)."""
    prompt = user_prompt
    if error_context:
        prompt += f"\n\n## Previous Error\n\n{error_context}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = invoke_agent(backend, system_prompt, prompt, model, max_tokens)
            if result and result.strip():
                return result
            print(f"  Empty response on attempt {attempt}/{MAX_RETRIES}")
        except Exception as e:
            print(f"  Error on attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt == MAX_RETRIES:
                raise
            prompt = user_prompt + f"\n\n## Previous Error (attempt {attempt})\n\n{e}"
    return ""


def inject_variables(template: str, variables: dict[str, str]) -> str:
    """Replace {{VARIABLE}} placeholders in a template."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


LAYERS = ["domain", "data", "presentation", "view"]


def run_secretary(backend: str, project_root: Path, model: str | None, app_target: str) -> str:
    """Invoke Secretary AI and return project status."""
    status_path = project_root / "ai-framework" / "PROJECT_STATUS.md"
    previous_status = read_file_if_exists(status_path)

    if previous_status:
        print("Secretary AI — Incremental update (previous status found)...")
    else:
        print("Secretary AI — Full scan (no previous status)...")

    contract = load_contract("secretary", project_root)
    prompt = load_prompt("secretary", project_root)
    output_format = load_output_format(project_root)

    variables = {
        "PROJECT_ROOT": str(project_root),
        "PREVIOUS_STATUS": previous_status,
        "APP_TARGET": app_target,
        "TIMESTAMP": subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
    }

    system = inject_variables(contract, variables)
    user = inject_variables(prompt + "\n\n" + output_format, variables)

    secretary_output = invoke_agent_with_retry(backend, system, user, model)

    # Parse structured output and write files
    parse_result = parse_output(secretary_output, project_root)
    if parse_result.files:
        written = write_files(parse_result, project_root)
        for path in written:
            print(f"  Written: {path}")
    else:
        # Fallback: write raw output if no file blocks found
        status_path.write_text(secretary_output)
        print(f"  Written (raw): {status_path}")

    return read_file_if_exists(status_path)


def run_layer_cycle(
    backend: str,
    project_root: Path,
    feature: str,
    model: str | None,
    layer: str,
    project_status: str,
    arch_output: str,
    app_target: str,
) -> tuple[str, str]:
    """Run a single layer cycle: Unit Test -> Code -> diff gate. Returns (ut_output, code_output)."""
    ut_conventions = read_file_if_exists(project_root / "ai-framework" / "references" / "unit-test-conventions.md")
    output_format = load_output_format(project_root)

    if layer != "view":
        print(f"  Unit Test AI — Writing {layer} layer tests...")
        ut_contract = load_contract("unit-test", project_root)
        ut_prompt = load_prompt("unit-test", project_root)

        variables = {
            "FEATURE_REQUEST": feature,
            "PROJECT_STATUS": project_status,
            "PROTOCOL_FILES": arch_output,
            "UNIT_TEST_CONVENTIONS": ut_conventions,
            "CURRENT_LAYER": layer,
        }
        system = inject_variables(ut_contract, variables)
        user = inject_variables(ut_prompt + "\n\n" + output_format, variables)

        ut_output = invoke_agent_with_retry(backend, system, user, model)

        # Parse and write test files
        ut_result = parse_output(ut_output, project_root)
        if ut_result.files:
            written = write_files(ut_result, project_root)
            for path in written:
                print(f"  Written: {path}")
        print(ut_output[:200] + "..." if len(ut_output) > 200 else ut_output)
    else:
        ut_output = ""

    print(f"  Code AI — Implementing {layer} layer...")
    code_contract = load_contract("code", project_root)
    code_prompt = load_prompt("code", project_root)

    variables = {
        "FEATURE_REQUEST": feature,
        "PROJECT_STATUS": project_status,
        "PROTOCOL_FILES": arch_output,
        "UNIT_TEST_FILES": ut_output,
        "CURRENT_LAYER": layer,
    }
    system = inject_variables(code_contract, variables)
    user = inject_variables(code_prompt + "\n\n" + output_format, variables)

    # Code AI with test failure retry
    code_output = invoke_agent_with_retry(backend, system, user, model)

    # Parse and write code files
    code_result = parse_output(code_output, project_root)
    if code_result.files:
        written = write_files(code_result, project_root)
        for path in written:
            print(f"  Written: {path}")

    # Run tests and retry if they fail
    test_proc = subprocess.run(
        ["swift", "test"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if test_proc.returncode != 0:
        print("  Tests failed. Retrying Code AI with failure context...")
        error_ctx = test_proc.stdout + test_proc.stderr
        code_output = invoke_agent_with_retry(
            backend, system, user, model,
            error_context=f"Test failures:\n{error_ctx[-2000:]}",
        )
        code_result = parse_output(code_output, project_root)
        if code_result.files:
            write_files(code_result, project_root)

    # Execute any action blocks
    if code_result.actions:
        execute_actions(code_result, project_root)

    print(code_output[:200] + "..." if len(code_output) > 200 else code_output)

    return ut_output, code_output


def run_workflow(backend: str, feature: str, model: str | None = None, app_target: str = "App"):
    """Run the full orchestrator workflow with bottom-up layer cycles."""
    project_root = get_project_root()
    print(f"Project root: {project_root}")
    print(f"Backend: {backend}")
    print(f"Feature: {feature}")
    print(f"App target: {app_target}")
    print()

    # Secretary
    print("=" * 60)
    print("Phase 1: Secretary + Architecture")
    print("=" * 60)
    project_status = run_secretary(backend, project_root, model, app_target)
    print()

    # Architecture (runs once)
    print("Architecture AI — Planning package structure + layer decomposition...")
    arch_contract = load_contract("architecture", project_root)
    arch_prompt = load_prompt("architecture", project_root)
    output_format = load_output_format(project_root)

    variables = {
        "FEATURE_REQUEST": feature,
        "PROJECT_STATUS": project_status,
        "PROJECT_ROOT": str(project_root),
    }
    system = inject_variables(arch_contract, variables)
    user = inject_variables(arch_prompt + "\n\n" + output_format, variables)

    arch_output = invoke_agent_with_retry(backend, system, user, model)
    print(arch_output)
    print()

    # Gate 1: Human Review
    print("=" * 60)
    print("GATE 1: Human Review")
    print("=" * 60)
    print("Review the architecture plan above.")
    approval = input("Approve? (y/n): ")
    if approval.lower() != "y":
        print("Revise the feature request and re-run.")
        return
    print()

    # Parse and write architecture files
    arch_result = parse_output(arch_output, project_root)
    if arch_result.files:
        written = write_files(arch_result, project_root)
        for path in written:
            print(f"  Written: {path}")
    if arch_result.actions:
        execute_actions(arch_result, project_root)

    if check_diff_gate(project_root, feature):
        print("Restarting from new base after architecture...")
        project_status = run_secretary(backend, project_root, model, app_target)

    # Layer cycles: Domain -> Data -> Presentation -> View
    all_code_output = ""
    all_ut_output = ""

    for i, layer in enumerate(LAYERS):
        cycle_num = i + 1
        print("=" * 60)
        print(f"Cycle {cycle_num}: {layer.title()} Layer")
        print("=" * 60)

        if cycle_num > 1:
            project_status = run_secretary(backend, project_root, model, app_target)

        ut_output, code_output = run_layer_cycle(
            backend, project_root, feature, model,
            layer, project_status, arch_output, app_target,
        )
        all_ut_output += ut_output
        all_code_output += code_output

        if layer == "view":
            print("  UI Test AI — Writing UI tests...")
            ui_contract = load_contract("ui-test", project_root)
            ui_prompt = load_prompt("ui-test", project_root)

            variables = {
                "FEATURE_REQUEST": feature,
                "PROJECT_STATUS": project_status,
                "PROTOCOL_FILES": arch_output,
                "PRODUCTION_CODE": all_code_output,
                "UNIT_TEST_FILES": all_ut_output,
            }
            system = inject_variables(ui_contract, variables)
            user = inject_variables(ui_prompt + "\n\n" + output_format, variables)

            ui_output = invoke_agent_with_retry(backend, system, user, model, max_tokens=32768)

            # Parse and write UI test files
            ui_result = parse_output(ui_output, project_root)
            if ui_result.files:
                written = write_files(ui_result, project_root)
                for path in written:
                    print(f"  Written: {path}")
            if ui_result.actions:
                execute_actions(ui_result, project_root)

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
    parser.add_argument(
        "--app-target",
        default="App",
        help="App target name (default: App)",
    )
    args = parser.parse_args()

    run_workflow(args.backend, args.feature, args.model, args.app_target)


if __name__ == "__main__":
    main()
