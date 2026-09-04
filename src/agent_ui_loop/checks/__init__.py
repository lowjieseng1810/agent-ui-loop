from __future__ import annotations

from agent_ui_loop.checks.clipping import ElementInViewportCheck, NoClippingCheck
from agent_ui_loop.checks.console import ConsoleErrorsCheck
from agent_ui_loop.checks.element import ElementExistsCheck, ElementVisibleCheck
from agent_ui_loop.checks.images import BrokenImagesCheck
from agent_ui_loop.checks.network import NetworkFailuresCheck
from agent_ui_loop.checks.overflow import OverflowCheck
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
}


def run_requirement(requirement: Requirement, ctx):
    check = REGISTRY.get(requirement.type)
    if check is None:
        raise UserError(
            what=f"no implementation for check type {requirement.type}",
            why="the requirement type is recognized but not registered.",
            fix="update Agent UI Loop or remove the requirement.",
        )
    return check.run(requirement, ctx)
