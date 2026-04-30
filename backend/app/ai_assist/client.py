"""Anthropic API client wrapper for AI Assist calls.

Centralizes API-key handling, model/timeout configuration, and the
specific tool-use call pattern we depend on. The rest of the AI Assist
code never imports `anthropic` directly — they go through this module
so the integration surface stays small and mockable.
"""

import logging
import os
from typing import Any

import anthropic

MODEL_ID = "claude-sonnet-4-6"
MAX_TOKENS = 2048
TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)


class AIAssistError(Exception):
    """Base error for the AI Assist subsystem."""


class AIAssistNotConfigured(AIAssistError):
    """Raised when no API key is available."""


class AIAssistCallFailed(AIAssistError):
    """Raised when the model API call errors or returns no tool use."""


def _get_anthropic_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIAssistNotConfigured(
            "ANTHROPIC_API_KEY environment variable is not set."
        )
    return anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT_SECONDS)


def call_with_tool(
    system: str,
    user_message: str,
    tool_definition: dict[str, Any],
) -> dict[str, Any]:
    """Calls the model and returns the structured tool-input dict.

    Forces `tool_choice` so the model cannot reply with prose — it
    must invoke the tool, which means the result is structurally
    guaranteed to match the tool's `input_schema`.

    Args:
        system: The system prompt.
        user_message: The user-role message content.
        tool_definition: A single Anthropic tool definition with
          `name`, `description`, and `input_schema` keys.

    Returns:
        The parsed `input` dict from the model's tool-use block.

    Raises:
        AIAssistNotConfigured: When `ANTHROPIC_API_KEY` is missing.
        AIAssistCallFailed: When the API call errors or the response
          contains no tool-use block.
    """
    client = _get_anthropic_client()
    try:
        response = client.messages.create(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            tools=[tool_definition],
            tool_choice={"type": "tool", "name": tool_definition["name"]},
        )
    except anthropic.APIError as exc:
        logger.exception("Anthropic API call failed")
        raise AIAssistCallFailed(str(exc)) from exc

    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)

    raise AIAssistCallFailed("Model response did not contain a tool-use block.")
