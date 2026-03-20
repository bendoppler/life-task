# Structured Output Convention

All agents that produce files use a standard fenced-block format. This is the core mechanism that makes the framework platform-agnostic.

## File Blocks

Output code in fenced blocks with a language and relative file path:

````
```swift:Packages/TaskList/Sources/TaskListProtocol/TaskListProviding.swift
public protocol TaskListProviding {
    func allTasks() async throws -> [TaskItem]
}
```
````

Format: `` ```<language>:<relative-path-from-project-root> ``

## Update Blocks

When modifying existing files (e.g., `modules.yml`, root `Package.swift`), use the `(append)` modifier:

````
```yaml:modules.yml (append)
  - protocol: TaskListProviding
    module: TaskListModule
    package: TaskList
    protocolPackage: TaskListProtocol
```
````

## Action Blocks

Non-file operations use HTML comment syntax. The action vocabulary is a **closed set** — agents may only emit these actions:

| Action | Shell command | When used |
|--------|-------------|-----------|
| `swift-package-resolve` | `swift package resolve` | After Architecture AI creates Package.swift |
| `swift-test` | `swift test` | After Unit Test AI or Code AI |
| `swift-build` | `swift build` | After Code AI to verify compilation |
| `git-commit "msg"` | `git add -A && git commit -m "msg"` | At diff gate or end of workflow |
| `gh-pr-create "title"` | `gh pr create --title "title" --body "..."` | At diff gate or end of workflow |

```
<!-- ACTION: swift-package-resolve -->
<!-- ACTION: swift-test -->
<!-- ACTION: git-commit "feat(TaskList): domain layer" -->
<!-- ACTION: gh-pr-create "feat(TaskList): domain layer" -->
```

## Platform Handling

| Platform | File blocks | Action blocks |
|----------|------------|---------------|
| **CLI (Claude API / Ollama)** | `parser.py` extracts and writes files to disk | CLI executes shell commands |
| **Cursor** | Cursor writes files natively, uses blocks as guidance | User runs commands or Cursor executes |
| **Claude Code** | Claude Code writes files via native tools, uses blocks as guidance | Claude Code executes via Bash tool |

For Cursor and Claude Code, the structured blocks serve as clear instructions about what files to create and what content they should contain. The AI uses its native file-writing capabilities rather than outputting raw blocks.
