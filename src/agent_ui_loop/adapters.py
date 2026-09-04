"""Thin agent adapters. Core verification never lives here."""

from __future__ import annotations

from typing import Any


def format_for_agent(summary: dict[str, Any]) -> str:
    """Shared structured block any agent can parse."""
    import json

    return json.dumps(summary, indent=2)


ADAPTERS = {
    "claude-code": "See .claude/skills/agent-ui-loop/SKILL.md",
    "cursor": "See adapters/cursor/README.md",
    "codex": "See adapters/codex/README.md",
    "opencode": "See adapters/opencode/README.md",
}
