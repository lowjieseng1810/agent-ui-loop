from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement


class ConsoleErrorsCheck:
    type = "no-console-errors"
    description = "Fail on console.error / pageerror."
    domain = "runtime"
    scope = "page"
    why = "A completed UI should not throw in the browser console."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        errors = [
            entry
            for entry in ctx.console
            if entry.get("type") in {"error", "pageerror"}
        ]
        if errors:
            return result(
                requirement,
                ctx,
                "failed",
                {
                    "errorCount": len(errors),
                    "errors": errors[:20],
                },
                f"{len(errors)} console error(s) on {ctx.route}",
            )
        return result(
            requirement,
            ctx,
            "passed",
            {"errorCount": 0},
            "no console errors",
        )
