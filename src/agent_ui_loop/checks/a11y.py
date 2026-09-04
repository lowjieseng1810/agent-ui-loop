from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement

A11Y_JS = """
() => {
  const nodes = Array.from(document.querySelectorAll("button, a, input, select, textarea"));
  const missing = [];
  for (const el of nodes) {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (type === "hidden") continue;
    const text = (el.innerText || "").trim();
    const aria = (el.getAttribute("aria-label") || "").trim();
    const labelledBy = el.getAttribute("aria-labelledby");
    let labelled = false;
    if (labelledBy) {
      labelled = labelledBy.split(/\\s+/).some((id) => {
        const n = document.getElementById(id);
        return n && (n.innerText || "").trim();
      });
    }
    const id = el.getAttribute("id");
    const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : el.closest("label");
    const hasName = Boolean(text || aria || labelled || (label && (label.innerText || "").trim()));
    const role = el.getAttribute("role") || tag;
    if (!hasName) {
      missing.push({ tag, type, role, testid: el.getAttribute("data-testid") });
    }
  }
  return { interactiveCount: nodes.length, missing };
}
"""

CONTRAST_JS = """
(selector) => {
  const targets = selector
    ? Array.from(document.querySelectorAll(selector))
    : Array.from(document.querySelectorAll("button, a, p, h1, h2, h3, label"));
  function parse(c) {
    const m = c.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    if (!m) return null;
    return [Number(m[1]), Number(m[2]), Number(m[3])];
  }
  function lum(rgb) {
    const s = rgb.map((v) => {
      const x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * s[0] + 0.7152 * s[1] + 0.0722 * s[2];
  }
  const issues = [];
  for (const el of targets.slice(0, 40)) {
    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    const bg = parse(cs.backgroundColor);
    if (!fg || !bg || cs.backgroundColor === "rgba(0, 0, 0, 0)") continue;
    const L1 = lum(fg);
    const L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    if (ratio < 3) {
      issues.push({
        text: (el.innerText || "").slice(0, 40),
        ratio: Number(ratio.toFixed(2)),
        color: cs.color,
        backgroundColor: cs.backgroundColor,
      });
    }
  }
  return { measured: Math.min(targets.length, 40), issues };
}
"""


class A11yNamesCheck:
    type = "a11y-names"
    description = "Flag buttons/links/inputs with no accessible name."
    domain = "ui"
    scope = "page"
    why = "Interactive controls should be nameable by assistive tech."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        measured = ctx.page.evaluate(A11Y_JS)
        missing = measured.get("missing") or []
        evidence = {**measured}
        if missing:
            return result(
                requirement,
                ctx,
                "failed",
                evidence,
                f"{len(missing)} interactive element(s) missing an accessible name",
                why=self.why,
            )
        return result(requirement, ctx, "passed", evidence, "interactive elements have accessible names", why=self.why)


class A11yContrastCheck:
    type = "a11y-contrast"
    description = "Obvious text/background contrast failures where both colors are measurable."
    domain = "ui"
    scope = "page"
    why = "Very low contrast is a deterministic accessibility defect."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        measured = ctx.page.evaluate(CONTRAST_JS, requirement.selector)
        issues = measured.get("issues") or []
        if issues:
            return result(
                requirement,
                ctx,
                "failed",
                measured,
                f"{len(issues)} obvious contrast issue(s) (ratio < 3)",
                why=self.why,
            )
        return result(requirement, ctx, "passed", measured, "no obvious measurable contrast failures", why=self.why)
