"""Check result types. Core logic stays agent-agnostic."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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
    page: Any
    cwd: Path | None = None
    run_dir: Path | None = None
    color_scheme: str | None = None
    screenshots: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CheckResult:
    check: str
    status: str
    route: str
    viewport: dict[str, Any]
    evidence: dict[str, Any] = field(default_factory=dict)
    screenshot: str | None = None
    message: str = ""
    layer: int = 1
    actionable: bool = True
    selector: str | None = None
    why: str = ""
    domain: str = "ui"
    scope: str = "page"
    command: str | None = None

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
            "why": self.why,
            "domain": self.domain,
            "scope": self.scope,
        }
        if self.selector:
            payload["selector"] = self.selector
        if self.command:
            payload["command"] = self.command
        return payload


class Check(Protocol):
    type: str
    description: str
    domain: str
    scope: str
    why: str

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
    why: str = "",
    command: str | None = None,
) -> CheckResult:
    return CheckResult(
        check=requirement.type,
        status=status,
        route=ctx.route,
        viewport={
            "name": ctx.viewport.name,
            "width": ctx.viewport.width,
            "height": ctx.viewport.height,
            "colorScheme": ctx.color_scheme,
        },
        evidence=evidence,
        screenshot=ctx.screenshot,
        message=message,
        layer=layer,
        actionable=actionable,
        selector=requirement.selector,
        why=why,
        domain=requirement.domain,
        scope=requirement.scope,
        command=command,
    )
