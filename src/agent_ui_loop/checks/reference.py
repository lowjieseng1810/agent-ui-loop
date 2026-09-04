from __future__ import annotations

from pathlib import Path

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement


class ReferenceCompareCheck:
    type = "reference-compare"
    description = "Compare a captured screenshot to a reference image. Evidence of difference, not Percy."
    domain = "ui"
    scope = "run"
    why = "A reference image should be comparable to what the browser actually rendered."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        extra = requirement.extra or {}
        image = str(extra.get("image") or "")
        cwd = ctx.cwd or Path.cwd()
        ref = (cwd / image).resolve()
        try:
            ref.relative_to(cwd.resolve())
        except ValueError:
            return result(requirement, ctx, "failed", {"image": image}, "reference path escaped the project", why=self.why)
        if not ref.is_file():
            return result(requirement, ctx, "failed", {"image": image}, f"reference image missing: {image}", why=self.why)

        want_vp = extra.get("viewport")
        want_route = extra.get("route")
        shot_rel = None
        for shot in ctx.screenshots:
            if want_vp and shot.get("viewport") != want_vp:
                continue
            if want_route and shot.get("route") != want_route:
                continue
            shot_rel = shot.get("path")
            break
        if not shot_rel and ctx.screenshot:
            shot_rel = ctx.screenshot
        if not shot_rel or not ctx.run_dir:
            return result(requirement, ctx, "failed", {"image": image}, "no screenshot available to compare", why=self.why)
        actual = (ctx.run_dir / shot_rel).resolve()
        if not actual.is_file():
            return result(requirement, ctx, "failed", {"screenshot": shot_rel}, "screenshot file missing", why=self.why)

        try:
            from PIL import Image, ImageChops
        except ImportError:
            return result(
                requirement,
                ctx,
                "failed",
                {"image": image},
                "Pillow is required for reference-compare (pip install pillow)",
                why=self.why,
            )

        ref_img = Image.open(ref).convert("RGB")
        act_img = Image.open(actual).convert("RGB")
        if ref_img.size != act_img.size:
            act_img = act_img.resize(ref_img.size)
        diff = ImageChops.difference(ref_img, act_img)
        hist = diff.histogram()
        # Sum of all channel bins except 0 (identical)
        pixels = ref_img.size[0] * ref_img.size[1]
        changed = 0
        for channel in range(3):
            ch = hist[channel * 256 : (channel + 1) * 256]
            changed += sum(ch[i] * i for i in range(1, 256))
        # Normalize to 0..1-ish ratio of mean channel delta
        mean_delta = (changed / 3) / (pixels * 255) if pixels else 1
        out_path = ctx.run_dir / "screenshots" / "reference-diff.png"
        diff.save(out_path)
        threshold = extra.get("maxDiffRatio")
        evidence = {
            "reference": image,
            "screenshot": shot_rel,
            "diff": "screenshots/reference-diff.png",
            "meanDelta": round(float(mean_delta), 4),
            "maxDiffRatio": threshold,
            "resized": True,
        }
        layer = 2
        actionable = False
        status = "passed"
        message = f"reference compared (meanDelta={mean_delta:.3f})"
        if threshold is not None and float(mean_delta) > float(threshold):
            status = "failed"
            layer = 1
            actionable = True
            message = f"reference mismatch meanDelta={mean_delta:.3f} > {threshold}"
        return result(
            requirement,
            ctx,
            status,
            evidence,
            message,
            layer=layer,
            actionable=actionable,
            why=self.why,
        )
