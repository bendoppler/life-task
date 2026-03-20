# Secretary AI Contract

## Role

Scans the project and produces a comprehensive status report (`PROJECT_STATUS.md`) that other agents consume as context. Runs at the start of each cycle (not before every agent).

## Input

| Variable | Type | Description |
|----------|------|-------------|
| `PROJECT_ROOT` | path | Absolute path to the monorepo root |
| `PREVIOUS_STATUS` | markdown (optional) | Contents of existing `PROJECT_STATUS.md` if it exists. Used as baseline for incremental updates. If absent, perform a full scan. |
| `APP_TARGET` | string | Name of the app target directory (e.g., `MyApp`). Used to locate UI test targets and test fixtures. |
| `TIMESTAMP` | string | ISO 8601 timestamp for the report header. |

## Output

A file block containing `ai-framework/PROJECT_STATUS.md` with the following required sections:

### Required Sections

```markdown
# Project Status

Generated: {{TIMESTAMP}}

## Packages
- List every Swift package in `Packages/` with its `Package.swift` targets
- For each target: name, type (library/executable/test), dependencies

## Protocols
- List every public protocol across all Protocol targets
- File path, protocol name, methods/properties

## Source Files
- Per package: list of source files with one-line summary of purpose
- Group by target (Protocol vs Implementation)

## Unit Tests
- Per package: list of test files
- For each: suite name, number of tests, what they cover

## UI Tests
- List of UI test files
- For each: flow name, page objects used, stubs used

## Modules Registry
- Contents of `modules.yml`
- List of registered modules and their protocol-to-implementation mapping

## Test Results
- Last known test pass/fail status per package
- Output of `swift test` if available

## Git Status
- Current branch
- Cumulative diff size (insertions + deletions) since last commit
- Warning if approaching 500-line limit
```

## Behavior Rules

1. **Read existing status first.** If `PROJECT_STATUS.md` exists, load it as the baseline. Use `git diff --name-only` to detect which files changed, and only re-scan the affected sections. Keep unchanged sections from the previous status.
2. **Full scan on first run.** If no `PROJECT_STATUS.md` exists, scan everything from scratch.
3. **Always refresh runtime sections.** Test Results and Git Status must always be re-checked (they depend on runtime state, not just files).
4. If a section has no items (e.g., no UI tests yet), write "None" -- never omit the section.
5. Include file paths relative to `PROJECT_ROOT`.
6. For test results, run `swift test --skip-build` if a build exists, otherwise note "Not yet built".
7. For git status, run `git diff --stat HEAD` and sum insertions + deletions.
