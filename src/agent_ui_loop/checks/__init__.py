from __future__ import annotations

from agent_ui_loop.checks.a11y import A11yContrastCheck, A11yNamesCheck
from agent_ui_loop.checks.clipping import ElementInViewportCheck, NoClippingCheck
from agent_ui_loop.checks.command import CommandCheck
from agent_ui_loop.checks.console import ConsoleErrorsCheck
from agent_ui_loop.checks.element import ElementExistsCheck, ElementVisibleCheck
from agent_ui_loop.checks.files import FileExistsCheck
from agent_ui_loop.checks.httpcheck import HttpStatusCheck, RouteAvailableCheck
from agent_ui_loop.checks.images import BrokenImagesCheck
from agent_ui_loop.checks.network import NetworkFailuresCheck
from agent_ui_loop.checks.overflow import OverflowCheck
from agent_ui_loop.checks.reference import ReferenceCompareCheck
from agent_ui_loop.config import Requirement
from agent_ui_loop.errors import UserError

REGISTRY = {
    "no-console-errors": ConsoleErrorsCheck(),
    "no-network-failures": NetworkFailuresCheck(),
    "element-exists": ElementExistsCheck(),
    "element-visible": ElementVisibleCheck(),
    "no-horizontal-overflow": OverflowCheck(),
    "no-broken-images": BrokenImagesCheck(),
    "element-in-viewport": ElementInViewportCheck(),
    "no-clipping": NoClippingCheck(),
    "a11y-names": A11yNamesCheck(),
    "a11y-contrast": A11yContrastCheck(),
    "http-status": HttpStatusCheck(),
    "route-available": RouteAvailableCheck(),
    "file-exists": FileExistsCheck(),
    "command": CommandCheck(),
    "reference-compare": ReferenceCompareCheck(),
}


def describe_checks() -> list[dict]:
    rows = []
    for name, check in sorted(REGISTRY.items()):
        rows.append(
            {
                "type": name,
                "description": getattr(check, "description", ""),
                "domain": getattr(check, "domain", "ui"),
                "scope": getattr(check, "scope", "page"),
                "why": getattr(check, "why", ""),
            }
        )
    return rows


def run_requirement(requirement: Requirement, ctx):
    check = REGISTRY.get(requirement.type)
    if check is None:
        raise UserError(
            what=f"no implementation for check type {requirement.type}",
            why="the requirement type is recognized but not registered.",
            fix="update Agent UI Loop or remove the requirement.",
        )
    outcome = check.run(requirement, ctx)
    if not outcome.why:
        outcome.why = getattr(check, "why", "")
    return outcome
