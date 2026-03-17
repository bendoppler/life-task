"""Ollama local model backend adapter."""

import httpx


def invoke(
    prompt: str,
    model: str = "qwen2.5-coder:32b",
    base_url: str = "http://localhost:11434",
) -> str:
    """Send a prompt to Ollama and return the response text."""
    response = httpx.post(
        f"{base_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300.0,
    )
    response.raise_for_status()
    return response.json()["response"]
