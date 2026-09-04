#!/usr/bin/env python3
"""Build README visual assets from a REAL demo run. No fabricated UI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from agent_ui_loop.demo import demo_config, find_free_port, start_demo_server, write_demo_app
from agent_ui_loop.proof import build_proof, previous_run_dir, render_proof_text
from agent_ui_loop.runner import run_verification

ROOT = Path.cwd()
ASSETS = ROOT / "assets"
BG = (10, 14, 22)
PANEL = (17, 24, 39)
INK = (241, 245, 249)
MUTED = (148, 163, 184)
RED = (248, 113, 113)
GREEN = (52, 211, 153)
AMBER = (251, 191, 36)
LINE = (30, 41, 59)


def font(size: int, bold: bool = False):
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def mono(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def rounded(draw, xy, r, fill):
    draw.rounded_rectangle(xy, radius=r, fill=fill)


def save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    print("wrote", path)


def annotate_fail(shot: Image.Image, scroll: int, vw: int, overflow: int) -> Image.Image:
    """Keep the 390px viewport intact (intentional CTA clip) and put measurements on a wider canvas."""
    img = shot.convert("RGB")
    top = min(360, img.height - 360)
    crop = img.crop((0, top, img.width, min(img.height, top + 360)))
    banner_h = 100
    gutter = 220
    pad = 16
    canvas = Image.new("RGB", (pad + crop.width + gutter + pad, banner_h + pad + crop.height + pad), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, canvas.width, banner_h), fill=(127, 29, 29))
    draw.text((20, 14), "✗  ACCEPTANCE FAILED", fill=INK, font=font(22, True))
    draw.text((20, 48), "Mobile viewport 390×844  ·  CTA exceeds the viewport (detected overflow)", fill=(254, 202, 202), font=font(14))
    draw.text(
        (20, 72),
        f"scrollWidth={scroll}   viewportWidth={vw}   overflowPx={overflow}",
        fill=INK,
        font=mono(15),
    )
    ox, oy = pad, banner_h + pad
    canvas.paste(crop, (ox, oy))
    draw.rectangle((ox, oy, ox + crop.width, oy + crop.height), outline=RED, width=3)
    draw.line((ox + crop.width, oy, ox + crop.width, oy + crop.height), fill=RED, width=4)
    gx = ox + crop.width + 16
    draw.text((gx, oy + 40), "390px", fill=RED, font=font(20, True))
    draw.text((gx, oy + 70), "viewport", fill=INK, font=font(16, True))
    draw.text((gx, oy + 96), "edge", fill=INK, font=font(16, True))
    draw.text((gx, oy + 150), f"+{overflow}px", fill=RED, font=font(22, True))
    draw.text((gx, oy + 182), "beyond", fill=MUTED, font=font(14))
    draw.text((gx, oy + 204), "viewport", fill=MUTED, font=font(14))
    draw.text((gx, oy + 250), "Bug in the page,", fill=MUTED, font=font(13))
    draw.text((gx, oy + 270), "not a cropped shot.", fill=MUTED, font=font(13))
    return canvas


def before_after(before: Image.Image, after: Image.Image) -> Image.Image:
    def card(src: Image.Image, title: str, ok: bool, caption: str) -> Image.Image:
        top = min(360, src.height - 380)
        crop = src.crop((0, top, src.width, min(src.height, top + 380)))
        header = 52
        footer = 36
        c = Image.new("RGB", (crop.width, header + crop.height + footer), PANEL)
        c.paste(crop, (0, header))
        d = ImageDraw.Draw(c)
        d.rectangle((0, 0, c.width, header), fill=(20, 83, 45) if ok else (127, 29, 29))
        d.text((12, 14), title, fill=GREEN if ok else RED, font=font(16, True))
        d.rectangle((0, header + crop.height, c.width, c.height), fill=(15, 23, 42))
        d.text((12, header + crop.height + 8), caption, fill=MUTED, font=font(13))
        return c

    left = card(before, "BEFORE  ·  ✗ FAILED", False, "390×844 viewport  ·  CTA clipped by the page")
    right = card(after, "AFTER  ·  ✓ VERIFIED", True, "390×844 viewport  ·  CTA fully visible")
    gap = 20
    canvas = Image.new("RGB", (left.width + right.width + gap + 32, left.height + 32), BG)
    canvas.paste(left, (16, 16))
    canvas.paste(right, (16 + left.width + gap, 16))
    return canvas


def proof_image(text: str) -> Image.Image:
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    keep: list[str] = []
    for ln in lines:
        if ln.startswith("AGENT ") or ln.startswith("─"):
            continue
        if ln.strip().startswith("/") or "asset-work" in ln or ln.strip().startswith("logs/"):
            continue
        keep.append(ln)
    result_ln = next((ln for ln in keep if ln.startswith("RESULT:")), None)
    body = [ln for ln in keep if not ln.startswith("RESULT:")]
    canvas = Image.new("RGB", (920, 640), BG)
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (20, 20, 900, 620), 16, PANEL)
    y = 40
    draw.text((44, y), "AGENT COMPLETION PROOF", fill=INK, font=font(22, True))
    y = 84
    for ln in body:
        color = INK
        draw.text((44, y), ln[:82], fill=color, font=mono(14))
        y += 22
        if y > 540:
            break
    if result_ln:
        draw.rectangle((36, 560, 884, 604), fill=(6, 78, 59))
        draw.text((48, 570), result_ln, fill=GREEN, font=font(20, True))
    return canvas


def terminal_image(log: str) -> Image.Image:
    # Keep a readable slice: claim, a failure line, verified ending
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    raw_lines = log.splitlines()
    picked: list[str] = []
    for ln in raw_lines:
        if any(
            k in ln
            for k in (
                'Agent:',
                "Loop:",
                "Opening real",
                "mobile",
                "no-horizontal-overflow",
                "scrollWidth",
                "RESULT:",
                "VERIFIED",
                "FAILED",
                "Applying the CSS",
                "Artifacts:",
            )
        ):
            picked.append(ln[:88])
    if len(picked) > 22:
        picked = picked[:12] + ["…"] + picked[-9:]
    canvas = Image.new("RGB", (920, 520), BG)
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (20, 20, 900, 500), 16, (8, 12, 18))
    draw.text((40, 36), "$ agent-ui-loop demo", fill=AMBER, font=mono(16))
    y = 72
    for ln in picked:
        color = MUTED
        if "VERIFIED" in ln or "RESULT: PASSED" in ln:
            color = GREEN
        elif "FAILED" in ln or "✗" in ln or "overflow" in ln:
            color = RED
        elif ln.startswith("$") or "Agent:" in ln:
            color = INK
        draw.text((40, y), ln, fill=color, font=mono(13))
        y += 18
        if y > 470:
            break
    return canvas


def social() -> Image.Image:
    img = Image.new("RGB", (1280, 640), BG)
    draw = ImageDraw.Draw(img)
    draw.text((80, 90), "AGENT UI LOOP", fill=MUTED, font=font(22, True))
    draw.text((80, 150), "Your agent can code.", fill=INK, font=font(48, True))
    draw.text((80, 214), "Now make it prove the UI.", fill=INK, font=font(48, True))
    chips = [
        ("DONE", PANEL, MUTED),
        ("VERIFY", PANEL, AMBER),
        ("✗ FAIL", (127, 29, 29), RED),
        ("EVIDENCE", PANEL, INK),
        ("✓ VERIFIED", (6, 78, 59), GREEN),
    ]
    x = 80
    for label, fill, fg in chips:
        w = 18 + int(font(18, True).getlength(label))
        rounded(draw, (x, 360, x + w + 20, 412), 10, fill)
        draw.text((x + 10, 372), label, fill=fg, font=font(18, True))
        x += w + 36
        if x < 1100:
            draw.text((x - 28, 372), "→", fill=LINE, font=font(18, True))
    draw.text((80, 500), "Agent UI Verification for AI coding agents", fill=MUTED, font=font(20))
    draw.text((80, 540), "Acceptance  ·  real browser  ·  evidence  ·  proof", fill=MUTED, font=font(18))
    return img


W, H = 1280, 720
HEAD_H = 72
LEFT_W = 860


def capture_login(url: str, width: int, height: int) -> Image.Image:
    """Real Chromium screenshot at an explicit viewport. Used only for GIF composition."""
    from io import BytesIO

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page.goto(url.rstrip("/") + "/login", wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(200)
            data = page.screenshot(type="png")
        finally:
            browser.close()
    return Image.open(BytesIO(data)).convert("RGB")


def fit_contain(img: Image.Image, tw: int, th: int) -> Image.Image:
    """Scale the entire image into the box. Never crop."""
    ratio = min(tw / img.width, th / img.height)
    nw, nh = max(1, int(img.width * ratio)), max(1, int(img.height * ratio))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def crop_desktop_ui(img: Image.Image) -> Image.Image:
    w, h = img.size
    return img.crop((0, int(h * 0.12), min(w, int(w * 0.55)), int(h * 0.92)))


def find_cta_rows(img: Image.Image) -> tuple[int, int] | None:
    px = img.load()
    w, h = img.size
    ys: list[int] = []
    for y in range(h):
        hits = 0
        for x in range(0, w, 2):
            r, g, b = px[x, y][:3]
            if abs(r - 37) < 45 and abs(g - 99) < 55 and b > 180:
                hits += 1
        if hits > w * 0.12:
            ys.append(y)
    if not ys:
        return None
    return min(ys), max(ys)


def crop_mobile_ui(img: Image.Image) -> Image.Image:
    """Keep the full 390px width and enough vertical room for form + CTA."""
    w, h = img.size
    band = find_cta_rows(img)
    if band:
        y0 = max(0, band[0] - 320)
        y1 = min(h, band[1] + 40)
    else:
        y0, y1 = int(h * 0.28), int(h * 0.88)
    return img.crop((0, y0, w, y1))


def highlight_cta(img: Image.Image) -> Image.Image:
    band = find_cta_rows(img)
    if not band:
        return img
    y0, y1 = max(0, band[0] - 10), min(img.height - 1, band[1] + 10)
    out = img.copy()
    draw = ImageDraw.Draw(out)
    draw.rectangle((3, y0, img.width - 4, y1), outline=(220, 38, 38), width=6)
    return out


def hero_stage(
    browser: Image.Image,
    *,
    kicker: str,
    title: str,
    rows: list[tuple[str, str, str]],
    footer: str,
    mood: str = "neutral",
    view: str = "desktop",
    viewport_px: int | None = None,
) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    bar = {"fail": (127, 29, 29), "ok": (6, 78, 59)}.get(mood, (15, 23, 42))
    draw.rectangle((0, 0, W, HEAD_H), fill=bar)
    draw.text((24, 12), kicker, fill=(226, 232, 240), font=font(16, True))
    draw.text((24, 36), title, fill=INK, font=font(28, True))

    pane = Image.new("RGB", (LEFT_W, H - HEAD_H), BG)
    pd = ImageDraw.Draw(pane)
    inner_w, inner_h = LEFT_W - 40, H - HEAD_H - 48
    fitted = fit_contain(browser.convert("RGB"), inner_w, inner_h)
    px = 20
    py = 16 + max(0, (inner_h - fitted.height) // 2)
    pane.paste(fitted, (px, py))
    if view == "mobile-fail" and viewport_px:
        scale = fitted.width / browser.width
        edge = px + int(viewport_px * scale)
        pd.rectangle((px, py, edge, py + fitted.height), outline=RED, width=3)
        pd.line((edge, py, edge, py + fitted.height), fill=RED, width=4)
        pd.text((px + 8, py + 8), "390px viewport", fill=RED, font=font(14, True))
        ox = min(edge + 8, px + fitted.width - 170)
        pd.text((ox, py + 8), "overflow →", fill=RED, font=font(14, True))
    elif view == "mobile-ok":
        pd.rectangle((px, py, px + fitted.width, py + fitted.height), outline=GREEN, width=3)
        tag = "390px viewport  ·  full CTA visible"
        tw = int(font(13, True).getlength(tag)) + 16
        tx = max(px, px + fitted.width - tw)
        pd.rectangle((tx, py + fitted.height - 28, px + fitted.width, py + fitted.height), fill=(6, 78, 59))
        pd.text((tx + 8, py + fitted.height - 24), tag, fill=INK, font=font(13, True))
    img.paste(pane, (0, HEAD_H))
    draw.rectangle((LEFT_W, HEAD_H, LEFT_W + 2, H), fill=LINE)

    rx = LEFT_W + 28
    y = HEAD_H + 28
    draw.text((rx, y), "VERIFICATION", fill=MUTED, font=font(14, True))
    y += 36
    for mark, label, kind in rows:
        color = {"pass": GREEN, "fail": RED, "warn": AMBER, "dim": MUTED}.get(kind, INK)
        draw.text((rx, y), mark, fill=color, font=font(22, True))
        draw.text((rx + 36, y + 2), label, fill=INK, font=font(20, True))
        y += 42
        if y > H - 90:
            break
    if footer:
        draw.text((rx, H - 48), footer, fill=MUTED, font=font(15))
    return img


def gif_frame(title: str, body: Image.Image | None, subtitle: str, *, fail=False, ok=False) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    bar = (127, 29, 29) if fail else ((6, 78, 59) if ok else PANEL)
    draw.rectangle((0, 0, W, HEAD_H), fill=bar)
    draw.text((24, 14), title, fill=INK, font=font(26, True))
    draw.text((24, 46), subtitle, fill=(226, 232, 240), font=font(16))
    if body is not None:
        img.paste(fit_contain(body.convert("RGB"), W, H - HEAD_H), (0, HEAD_H))
    return img


def write_svg_loop(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    steps = ["WRITE", "RUN", "VERIFY", "EVIDENCE", "FIX", "REVERIFY", "PROVE"]
    parts = []
    x = 20
    for i, s in enumerate(steps):
        parts.append(
            f'<rect x="{x}" y="36" width="120" height="48" rx="8" fill="#111827" stroke="#334155"/>'
            f'<text x="{x + 60}" y="66" text-anchor="middle" fill="#e2e8f0" font-family="DejaVu Sans, sans-serif" font-size="13">{s}</text>'
        )
        if i < len(steps) - 1:
            parts.append(
                f'<text x="{x + 132}" y="66" fill="#64748b" font-family="DejaVu Sans, sans-serif" font-size="16">→</text>'
            )
        x += 148
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="120" viewBox="0 0 1080 120">
  <rect width="1080" height="120" fill="#0b1220"/>
  {"".join(parts)}
</svg>
'''
    path.write_text(svg, encoding="utf-8")
    print("wrote", path)


def write_svg_acceptance(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="180" viewBox="0 0 920 180">
  <rect width="920" height="180" fill="#0b1220"/>
  <text x="32" y="40" fill="#94a3b8" font-family="DejaVu Sans, sans-serif" font-size="14">ACCEPTANCE CRITERIA</text>
  <text x="32" y="78" fill="#e2e8f0" font-family="DejaVu Sans, sans-serif" font-size="22">YAML contract</text>
  <text x="260" y="78" fill="#64748b" font-size="22">→</text>
  <text x="300" y="40" fill="#94a3b8" font-family="DejaVu Sans, sans-serif" font-size="14">REAL BROWSER</text>
  <text x="300" y="78" fill="#e2e8f0" font-family="DejaVu Sans, sans-serif" font-size="22">Playwright Chromium</text>
  <text x="560" y="78" fill="#64748b" font-size="22">→</text>
  <text x="600" y="40" fill="#94a3b8" font-family="DejaVu Sans, sans-serif" font-size="14">EVIDENCE</text>
  <text x="600" y="78" fill="#e2e8f0" font-family="DejaVu Sans, sans-serif" font-size="22">shots · logs · numbers</text>
  <text x="32" y="140" fill="#34d399" font-family="DejaVu Sans, sans-serif" font-size="20">PROOF · auditable, not cryptographic</text>
</svg>
'''
    path.write_text(svg, encoding="utf-8")
    print("wrote", path)


def main() -> None:
    work = ROOT / ".agent-ui-loop" / "asset-work"
    if work.exists():
        shutil.rmtree(work)
    app = write_demo_app(work / "app", broken=True)
    port = find_free_port(48741)
    server = start_demo_server(app, port)
    url = f"http://127.0.0.1:{port}"
    try:
        cfg = demo_config(url)
        before = run_verification(cfg, cwd=work)
        overflow = next(
            r
            for r in before["results"]
            if r["check"] == "no-horizontal-overflow" and r["status"] == "failed"
        )
        ev = overflow["evidence"]
        sw, vw = int(ev["scrollWidth"]), int(ev["viewportWidth"])
        overflow_px = int(ev.get("overflowPx") or (sw - vw))
        wide = max(sw + 80, 680)
        fail_wide = capture_login(url, wide, 844)
        desk_live = capture_login(url, 1440, 900)
        write_demo_app(app, broken=False)
        ok_390 = capture_login(url, 390, 844)
        after = run_verification(cfg, cwd=work)
    finally:
        server.shutdown()
        server.server_close()

    bdir = Path(before["meta"]["runDir"])
    adir = Path(after["meta"]["runDir"])
    fail_shot = Image.open(next((bdir / "screenshots").glob("mobile*.png"))).convert("RGB")
    ok_shot = Image.open(next((adir / "screenshots").glob("mobile*.png"))).convert("RGB")

    proof_text = (adir / "proof.txt").read_text(encoding="utf-8")
    # Copy raw artifacts for docs
    raw = ROOT / "assets" / "examples"
    raw.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(adir / "proof.txt", ROOT / "docs" / "sample-proof.txt")
    shutil.copyfile(adir / "github.md", ROOT / "docs" / "sample-github-comment.md")
    shutil.copyfile(adir / "proof.json", raw / "proof.json")

    fail = annotate_fail(fail_shot, sw, vw, overflow_px)
    save(fail, ASSETS / "screenshots" / "mobile-failure.png")
    save(before_after(fail_shot, ok_shot), ASSETS / "screenshots" / "before-after.png")
    save(proof_image(proof_text), ASSETS / "screenshots" / "proof.png")
    save(social(), ASSETS / "social" / "github-social-preview.png")
    write_svg_loop(ASSETS / "diagrams" / "verification-loop.svg")
    write_svg_acceptance(ASSETS / "diagrams" / "acceptance-flow.svg")

    desk_ui = crop_desktop_ui(desk_live)
    fail_ui = crop_mobile_ui(fail_wide)
    ok_ui = crop_mobile_ui(ok_390)

    gif_frames = [
        hero_stage(
            desk_ui,
            kicker="AGENT UI LOOP",
            title='Agent: “Done.”     Loop: “Prove it.”',
            rows=[
                ("•", 'Agent: “Done.”', "dim"),
                ("▶", "Loop: Prove it.", "warn"),
                ("•", "No evidence yet", "warn"),
                ("▶", "Open real Chromium", "warn"),
            ],
            footer="Acceptance  ·  browser  ·  evidence  ·  proof",
            view="desktop",
        ),
        hero_stage(
            desk_ui,
            kicker="ACCEPTANCE",
            title="What does “Done” mean?",
            rows=[
                ("✓", "CTA visible", "pass"),
                ("✓", "Form functional", "pass"),
                ("…", "Mobile layout valid", "warn"),
                ("▶", "Chromium 1440×900 + 390×844", "warn"),
            ],
            footer="Explicit criteria — not a vibe",
            view="desktop",
        ),
        hero_stage(
            desk_ui,
            kicker="VERIFY  ·  DESKTOP",
            title="Desktop 1440×900  ·  PASS",
            rows=[
                ("✓", "desktop 1440×900", "pass"),
                ("…", "mobile 390×844 pending", "warn"),
                ("✓", "CTA / form / console", "pass"),
            ],
            footer="Desktop can pass while mobile fails",
            mood="ok",
            view="desktop",
        ),
        hero_stage(
            fail_ui,
            kicker="VERIFY  ·  MOBILE",
            title="✗  ACCEPTANCE FAILED",
            rows=[
                ("✓", "desktop 1440×900", "pass"),
                ("✗", "MOBILE OVERFLOW", "fail"),
                ("✗", f"scrollWidth={sw}", "fail"),
                ("✗", f"viewportWidth={vw}", "fail"),
                ("✗", f"overflowPx={overflow_px}", "fail"),
            ],
            footer="Red line = 390px viewport; full CTA in capture",
            mood="fail",
            view="mobile-fail",
            viewport_px=vw,
        ),
        hero_stage(
            fail_ui,
            kicker="EVIDENCE",
            title="Not a guess. Measured.",
            rows=[
                ("▣", "screenshot captured", "warn"),
                ("▣", f"scrollWidth {sw} > {vw}", "fail"),
                ("▣", f"overflowPx={overflow_px}", "fail"),
                ("→", "Agent reads the failure", "dim"),
            ],
            footer="Evidence on disk under .agent-ui-loop/",
            mood="fail",
            view="mobile-fail",
            viewport_px=vw,
        ),
        hero_stage(
            ok_ui,
            kicker="FIX  ·  SAMPLE APP ONLY",
            title="Demo constrains the CTA in CSS",
            rows=[
                ("!", "Does not edit your repository", "warn"),
                ("→", "agent-ui-loop demo", "dim"),
                ("→", "applies sample CSS fix", "dim"),
                ("→", "then reverifies", "dim"),
            ],
            footer="Honest workflow: evidence → you/agent fix → re-run",
            view="mobile-ok",
        ),
        hero_stage(
            ok_ui,
            kicker="REVERIFY",
            title="Same acceptance. Same browser.",
            rows=[
                ("✓", "desktop 1440×900", "pass"),
                ("✓", "mobile 390×844", "pass"),
                ("✓", "CTA fits the viewport", "pass"),
            ],
            footer="Re-run until the claim matches the UI",
            mood="ok",
            view="mobile-ok",
        ),
        hero_stage(
            ok_ui,
            kicker="PROOF",
            title="✓  VERIFIED",
            rows=[
                ("✓", "Acceptance passed", "pass"),
                ("✓", "Evidence retained", "pass"),
                ("✓", "PROOF GENERATED", "pass"),
                ("✓", "Claim is now testable", "pass"),
            ],
            footer="Auditable evidence — not cryptography",
            mood="ok",
            view="mobile-ok",
        ),
    ]
    dest = ASSETS / "hero" / "agent-ui-loop-demo.gif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    durations = [1100, 1100, 1100, 2800, 2000, 1800, 1600, 2500]
    quantized = []
    for fr in gif_frames:
        try:
            quantized.append(fr.convert("P", palette=Image.Palette.ADAPTIVE, colors=96))
        except AttributeError:
            quantized.append(fr.convert("P", palette=Image.ADAPTIVE, colors=96))
    quantized[0].save(
        dest,
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    shutil.copyfile(dest, ROOT / "docs" / "demo.gif")
    save(gif_frames[3], ASSETS / "hero" / "agent-ui-loop-hero.png")
    preview = ASSETS / "hero" / "gif-preview"
    preview.mkdir(parents=True, exist_ok=True)
    for i, fr in enumerate(gif_frames):
        save(fr, preview / f"frame-{i:02d}.png")
    print("wrote", dest, "duration_ms", sum(durations), file=sys.stderr)

    # stills for docs
    stills = ROOT / "docs" / "stills"
    stills.mkdir(parents=True, exist_ok=True)
    fail_shot.save(stills / "mobile-before.png")
    ok_shot.save(stills / "mobile-after.png")
    desk_live.save(stills / "desktop.png")

    meta = {
        "scrollWidth": sw,
        "viewportWidth": vw,
        "overflowPx": overflow_px,
        "beforeRun": str(bdir),
        "afterRun": str(adir),
    }
    (ASSETS / "examples" / "asset-source.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("source", meta)

    env = {**os.environ, "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}
    cmd = [sys.executable, "-m", "agent_ui_loop", "demo"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    demo_log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    log_path = ASSETS / "screenshots" / "demo-run.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(demo_log, encoding="utf-8")
    save(terminal_image(demo_log), ASSETS / "screenshots" / "terminal-verified.png")
    (ASSETS / "examples" / "demo-exit.json").write_text(
        json.dumps({"returncode": proc.returncode, "bytes": len(demo_log)}, indent=2) + "\n"
    )
    print("demo exit", proc.returncode)


if __name__ == "__main__":
    main()
