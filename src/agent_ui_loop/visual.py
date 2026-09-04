"""Optional visual reasoning (layer 2). Never required. Never auto-fails the run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class VisualFinding:
    title: str
    detail: str
    screenshot: str | None = None
    layer: int = 2
    actionable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "detail": self.detail,
            "screenshot": self.screenshot,
            "layer": self.layer,
            "actionable": self.actionable,
        }


class VisualProvider(Protocol):
    name: str

    def analyze(self, screenshot: Path, context: dict[str, Any]) -> list[VisualFinding]:
        """Return suggestions. Must not invent statistical confidence."""


class NoopVisualProvider:
    name = "none"

    def analyze(self, screenshot: Path, context: dict[str, Any]) -> list[VisualFinding]:
        return []


def resolve_provider(name: str | None) -> VisualProvider:
    if not name or name in {"none", "off", "false"}:
        return NoopVisualProvider()
    # Intentionally no bundled cloud provider. Adapters can register one later.
    return NoopVisualProvider()
