"""Check result types and registry. Core logic stays agent-agnostic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_ui_loop.config import Requirement, Viewport


@dataclass
class CheckContext:
    route: str
    url: str
    viewport: Viewport
    console: list[dict[str, Any]]
    network: list[dict[str, Any]]
    screenshot: str
    measurements: dict[str, Any]
    page: Any  # playwright Page; typed loosely to keep the core import-light


@dataclass
class CheckResult:
    check: str
    status: str  # passed | failed | error
    route: str
    viewport: dict[str, Any]
    evidence: dict[str, Any] = field(default_factory=dict)
    screenshot: str | None = None
    message: str = ""
    layer: int = 1
    actionable: bool = True
    selector: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "check": self.check,
            "status": self.status,
            "route": self.route,
            "viewport": self.viewport,
            "evidence": self.evidence,
            "screenshot": self.screenshot,
            "message": self.message,
            "layer": self.layer,
            "actionable": self.actionable,
        }
        if self.selector:
            payload["selector"] = self.selector
        return payload


class Check(Protocol):
    type: str

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult: ...


def result(
    requirement: Requirement,
    ctx: CheckContext,
    status: str,
    evidence: dict[str, Any],
    message: str,
    *,
    layer: int = 1,
    actionable: bool = True,
) -> CheckResult:
    return CheckResult(
        check=requirement.type,
        status=status,
        route=ctx.route,
        viewport={"name": ctx.viewport.name, "width": ctx.viewport.width, "height": ctx.viewport.height},
        evidence=evidence,
        screenshot=ctx.screenshot,
        message=message,
        layer=layer,
        actionable=actionable,
        selector=requirement.selector,
    )
