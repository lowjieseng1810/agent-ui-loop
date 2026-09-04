from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement

MEASURE_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) {
    return { exists: false };
  }
  const style = window.getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const intersects =
    rect.width > 0 &&
    rect.height > 0 &&
    rect.right > 0 &&
    rect.bottom > 0 &&
    rect.left < vw &&
    rect.top < vh;
  return {
    exists: true,
    tag: el.tagName,
    display: style.display,
    visibility: style.visibility,
    opacity: style.opacity,
    width: rect.width,
    height: rect.height,
    top: rect.top,
    left: rect.left,
    right: rect.right,
    bottom: rect.bottom,
    viewportWidth: vw,
    viewportHeight: vh,
    intersectsViewport: intersects,
    ariaHidden: el.getAttribute("aria-hidden"),
  };
}
"""


def _measure(ctx: CheckContext, selector: str) -> dict:
    return ctx.page.evaluate(MEASURE_JS, selector)


class ElementExistsCheck:
    type = "element-exists"

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        selector = requirement.selector or ""
        measured = _measure(ctx, selector)
        if not measured.get("exists"):
            return result(
                requirement,
                ctx,
                "failed",
                {"selector": selector, **measured},
                f"required element not found: {selector}",
            )
        return result(
            requirement,
            ctx,
            "passed",
            {"selector": selector, **measured},
            f"element exists: {selector}",
        )


class ElementVisibleCheck:
    type = "element-visible"

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        selector = requirement.selector or ""
        measured = _measure(ctx, selector)
        if not measured.get("exists"):
            return result(
                requirement,
                ctx,
                "failed",
                {"selector": selector, **measured},
                f"required element not found: {selector}",
            )
        hidden = (
            measured.get("display") == "none"
            or measured.get("visibility") == "hidden"
            or float(measured.get("opacity") or 1) == 0
            or float(measured.get("width") or 0) <= 0
            or float(measured.get("height") or 0) <= 0
        )
        playwright_visible = False
        try:
            locator = ctx.page.locator(selector).first
            playwright_visible = locator.is_visible()
        except Exception:
            playwright_visible = False
        visible = (not hidden) and playwright_visible
        evidence = {
            "selector": selector,
            "playwrightVisible": playwright_visible,
            **measured,
        }
        if not visible:
            return result(
                requirement,
                ctx,
                "failed",
                evidence,
                f"required element is not visible: {selector}",
            )
        return result(
            requirement,
            ctx,
            "passed",
            evidence,
            f"element visible: {selector}",
        )
