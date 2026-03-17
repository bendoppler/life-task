tech stack: swift ui, ui test, unit test, swift data if needed, backend can be flexible icloud or real backend service
I want to write the ai to help me write code for the project from scratch, my idea is:
- there is a master ai orchestration ai to invoke other ai agents to work:
1. architecture ai: this ai will understand the whole architecture of the project
2. ai write code: with protocol first to allow writing unit test
3. ai write unit test: i will provide later
4. secrectary ai
5. ai write ui test: after i code to pass unit test

The direction is test driven development: write unit test first, then write production code to pass, then write ui test

This setup must be agnostic can be used by cursor, claude or local model like Qwen 2.5 Coder using ollama