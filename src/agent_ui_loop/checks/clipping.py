from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement
from agent_ui_loop.checks.element import MEASURE_JS

CLIP_JS = """
() => {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const nodes = Array.from(document.querySelectorAll("[data-testid]"));
  return nodes.map((el) => {
    const r = el.getBoundingClientRect();
    const intersects =
      r.width > 0 &&
      r.height > 0 &&
      r.right > 0 &&
      r.bottom > 0 &&
      r.left < vw &&
      r.top < vh;
    const fullyInside =
      r.left >= -1 && r.top >= -1 && r.right <= vw + 1 && r.bottom <= vh + 1;
    return {
      testid: el.getAttribute("data-testid"),
      left: r.left,
      top: r.top,
      right: r.right,
      bottom: r.bottom,
      width: r.width,
      height: r.height,
      viewportWidth: vw,
      viewportHeight: vh,
      intersects,
      fullyInside,
    };
  });
}
"""


class ElementInViewportCheck:
    type = "element-in-viewport"
    description = "Require getBoundingClientRect to intersect the viewport."
    domain = "ui"
    scope = "page"
    why = "A required element must not sit fully outside the viewport."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        selector = requirement.selector or ""
        measured = ctx.page.evaluate(MEASURE_JS, selector)
        if not measured.get("exists"):
            return result(
                requirement,
                ctx,
                "failed",
                {"selector": selector, **measured},
                f"required element not found: {selector}",
            )
        if not measured.get("intersectsViewport"):
            return result(
                requirement,
                ctx,
                "failed",
                {"selector": selector, **measured},
                f"element is outside the viewport: {selector}",
            )
        return result(
            requirement,
            ctx,
            "passed",
            {"selector": selector, **measured},
            f"element intersects viewport: {selector}",
        )


class NoClippingCheck:
    """Fails when a [data-testid] element has no intersection with the viewport."""

    type = "no-clipping"
    description = "Flag [data-testid] nodes with no viewport intersection."
    domain = "ui"
    scope = "page"
    why = "Required testids should not be clipped out of view."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        if requirement.selector:
            inner = ElementInViewportCheck().run(requirement, ctx)
            inner.check = self.type
            return inner
        nodes = ctx.page.evaluate(CLIP_JS)
        outside = [n for n in nodes if not n.get("intersects")]
        if outside:
            return result(
                requirement,
                ctx,
                "failed",
                {"outsideCount": len(outside), "outside": outside[:20], "measuredCount": len(nodes)},
                f"{len(outside)} [data-testid] element(s) outside the viewport",
            )
        return result(
            requirement,
            ctx,
            "passed",
            {"outsideCount": 0, "measuredCount": len(nodes)},
            "no [data-testid] elements clipped out of the viewport",
        )
