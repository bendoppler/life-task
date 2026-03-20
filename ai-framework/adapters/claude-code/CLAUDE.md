# AI Framework

This project uses a multi-agent TDD framework for Swift development.

When asked to build a feature:
1. Follow the workflow in ai-framework/prompts/orchestrator.md
2. For each agent step, read the contract + prompt for that agent
3. Use your native tools (Read, Write, Edit, Bash) to execute —
   don't output structured blocks, write files directly
4. After Architecture AI step, present the plan and wait for approval
5. Respect the 500-line diff gate: check git diff --stat HEAD after each layer

Key paths:
- ai-framework/prompts/orchestrator.md
- ai-framework/contracts/
- ai-framework/references/
