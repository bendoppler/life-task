"""Claude API backend adapter."""

import anthropic


def invoke(prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Send a prompt to Claude API and return the response text."""
    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
    message = client.messages.create(
        model=model,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
