"""Anthropic SDK wrapper.

Wraps `client.messages.create` so each stage can call Claude with:
  - prompt caching on the system prompt (system prompts are stable per stage)
  - adaptive thinking (model decides how much to think)
  - optional server-side tools (web search / fetch)
  - pause_turn handling for long-running server-tool loops
"""

from __future__ import annotations

import os
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-opus-4-7"
WRITER_MODEL = "claude-sonnet-4-6"

WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20260209",
    "name": "web_search",
}
WEB_FETCH_TOOL: dict[str, Any] = {
    "type": "web_fetch_20260209",
    "name": "web_fetch",
}

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        _client = anthropic.AsyncAnthropic()
    return _client


def _extract_text(content_blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


async def call(
    *,
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16000,
    tools: list[dict[str, Any]] | None = None,
    effort: str = "high",
    max_continuations: int = 5,
) -> str:
    """Make a Claude call and return the final text response.

    Caches the system prompt (it's stable across cases — only the user turn changes).
    Loops on `pause_turn` so server-tool runs that exceed the default iteration cap
    can finish.
    """
    client = _get_client()

    system_blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    messages: list[dict[str, Any]] = [{"role": "user", "content": user}]

    request_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_blocks,
        "messages": messages,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort},
    }
    if tools:
        request_kwargs["tools"] = tools

    response = await client.messages.create(**request_kwargs)

    continuations = 0
    while response.stop_reason == "pause_turn" and continuations < max_continuations:
        messages.append({"role": "assistant", "content": response.content})
        response = await client.messages.create(**{**request_kwargs, "messages": messages})
        continuations += 1

    return _extract_text(response.content)
