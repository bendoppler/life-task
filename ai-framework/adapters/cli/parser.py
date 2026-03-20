"""
Output parser for AI agent structured output.

Extracts file blocks and action blocks from raw agent text output,
writes files to disk, and executes actions from a closed set.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileBlock:
    """A file block extracted from agent output."""
    language: str
    path: str
    content: str
    append: bool = False


@dataclass
class ParseResult:
    """Result of parsing agent output."""
    files: list[FileBlock] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


# Regex for file blocks: ```lang:path or ```lang:path (append)
_FILE_BLOCK_RE = re.compile(
    r"```(\w+):([^\s`]+?)(?:\s+\(append\))?\s*\n(.*?)```",
    re.DOTALL,
)

# Separate regex to detect append modifier
_FILE_BLOCK_APPEND_RE = re.compile(
    r"```(\w+):([^\s`]+?)\s+\(append\)\s*\n(.*?)```",
    re.DOTALL,
)

# Regex for action blocks: <!-- ACTION: command -->
_ACTION_RE = re.compile(r"<!--\s*ACTION:\s*(.+?)\s*-->")

# Closed set of allowed actions
_ALLOWED_ACTIONS = {
    "swift-test",
    "swift-build",
    "swift-package-resolve",
}
# These actions take a quoted argument
_ALLOWED_ACTIONS_WITH_ARG = {
    "git-commit",
    "gh-pr-create",
}


def parse_output(text: str, project_root: Path) -> ParseResult:
    """Extract file blocks and action blocks from agent output."""
    result = ParseResult()

    # Extract append blocks first (more specific pattern)
    append_paths = set()
    for match in _FILE_BLOCK_APPEND_RE.finditer(text):
        language, path, content = match.group(1), match.group(2), match.group(3)
        result.files.append(FileBlock(
            language=language,
            path=path,
            content=content,
            append=True,
        ))
        append_paths.add(path)

    # Extract non-append blocks
    for match in _FILE_BLOCK_RE.finditer(text):
        language, path, content = match.group(1), match.group(2), match.group(3)
        if path not in append_paths:
            result.files.append(FileBlock(
                language=language,
                path=path,
                content=content,
                append=False,
            ))

    # Extract action blocks
    for match in _ACTION_RE.finditer(text):
        result.actions.append(match.group(1).strip())

    return result


def write_files(result: ParseResult, project_root: Path) -> list[str]:
    """Write extracted file blocks to disk. Returns list of paths written."""
    written = []
    for block in result.files:
        target = project_root / block.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if block.append and target.exists():
            with open(target, "a") as f:
                f.write(block.content)
        else:
            target.write_text(block.content)
        written.append(str(target))
    return written


def execute_actions(result: ParseResult, project_root: Path) -> list[str]:
    """Execute action blocks (closed set only). Returns list of outputs."""
    outputs = []
    for action in result.actions:
        cmd = _resolve_action(action)
        if cmd is None:
            msg = f"WARNING: Unrecognized action '{action}' — skipped."
            print(msg)
            outputs.append(msg)
            continue

        print(f"  Executing: {cmd}")
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        output = proc.stdout + proc.stderr
        outputs.append(output)
        if proc.returncode != 0:
            print(f"  Action failed (exit {proc.returncode}): {output.strip()}")
        else:
            print(f"  Done.")
    return outputs


def _resolve_action(action: str) -> str | None:
    """Map an action string to a shell command, or None if unrecognized."""
    # Simple actions (no arguments)
    action_map = {
        "swift-test": "swift test",
        "swift-build": "swift build",
        "swift-package-resolve": "swift package resolve",
    }
    if action in action_map:
        return action_map[action]

    # Actions with quoted argument: git-commit "msg" or gh-pr-create "title"
    git_commit_match = re.match(r'^git-commit\s+"(.+)"$', action)
    if git_commit_match:
        msg = git_commit_match.group(1).replace('"', '\\"')
        return f'git add -A && git commit -m "{msg}"'

    pr_match = re.match(r'^gh-pr-create\s+"(.+)"$', action)
    if pr_match:
        title = pr_match.group(1).replace('"', '\\"')
        return f'gh pr create --title "{title}" --body "Auto-created by AI framework"'

    return None
