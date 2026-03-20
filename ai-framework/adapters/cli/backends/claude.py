"""Claude API backend adapter."""

import anthropic


def invoke(
    system_prompt: str = "",
    user_prompt: str = "",
    prompt: str = "",
    model: str | None = None,
    max_tokens: int = 16384,
) -> str:
    """Send a prompt to Claude API and return the response text.

    Args:
        system_prompt: Contract content sent as system message (role + rules).
        user_prompt: Prompt content sent as user message (process + examples).
        prompt: Legacy single-prompt mode (used if system_prompt/user_prompt not provided).
        model: Model to use (default: claude-sonnet-4-20250514).
        max_tokens: Maximum tokens in response (default: 16384).
    """
    if model is None:
        model = "claude-sonnet-4-20250514"

    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
    }

    if system_prompt:
        kwargs["system"] = system_prompt
        kwargs["messages"] = [{"role": "user", "content": user_prompt or prompt}]
    else:
        # Legacy mode: everything in user message
        kwargs["messages"] = [{"role": "user", "content": prompt or user_prompt}]

    message = client.messages.create(**kwargs)
    return message.content[0].text
