from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement

IMAGES_JS = """
() => {
  return Array.from(document.images).map((img) => {
    const src = img.currentSrc || img.getAttribute("src") || "";
    return {
      src,
      alt: img.alt || "",
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
    };
  });
}
"""


class BrokenImagesCheck:
    type = "no-broken-images"
    description = "Fail when img.complete && naturalWidth === 0."
    domain = "ui"
    scope = "page"
    why = "Broken images are a deterministic completion failure."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        images = ctx.page.evaluate(IMAGES_JS)
        broken = []
        for img in images:
            src = (img.get("src") or "").strip()
            if not src or src.startswith("data:"):
                continue
            if img.get("complete") and int(img.get("naturalWidth") or 0) == 0:
                broken.append(img)
        if broken:
            return result(
                requirement,
                ctx,
                "failed",
                {"brokenCount": len(broken), "broken": broken[:20], "imageCount": len(images)},
                f"{len(broken)} broken image(s)",
            )
        return result(
            requirement,
            ctx,
            "passed",
            {"brokenCount": 0, "imageCount": len(images)},
            "no broken images",
        )
