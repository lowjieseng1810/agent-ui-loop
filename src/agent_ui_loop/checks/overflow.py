from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement

OVERFLOW_JS = """
() => {
  const doc = document.documentElement;
  const body = document.body;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const scrollWidth = Math.max(doc.scrollWidth, body ? body.scrollWidth : 0);
  const clientWidth = doc.clientWidth;
  return {
    scrollWidth,
    clientWidth,
    viewportWidth,
    viewportHeight,
    overflowPx: Math.max(0, scrollWidth - viewportWidth),
  };
}
"""

# Subpixel / scrollbar slack. Real overflow is typically tens of pixels.
TOLERANCE_PX = 1


class OverflowCheck:
    type = "no-horizontal-overflow"
    description = "Compare document scrollWidth to the viewport width."
    domain = "ui"
    scope = "page"
    why = "The layout must fit the claimed viewport."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        measured = ctx.page.evaluate(OVERFLOW_JS)
        overflow = float(measured.get("overflowPx") or 0)
        failed = overflow > TOLERANCE_PX
        evidence = {**measured, "tolerancePx": TOLERANCE_PX}
        if failed:
            return result(
                requirement,
                ctx,
                "failed",
                evidence,
                (
                    f"horizontal overflow: scrollWidth={measured['scrollWidth']} "
                    f"viewportWidth={measured['viewportWidth']}"
                ),
            )
        return result(
            requirement,
            ctx,
            "passed",
            evidence,
            "no horizontal overflow",
        )
