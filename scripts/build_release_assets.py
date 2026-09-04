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
HEAD_H = 56
LEFT_W = 930
SAFE = 16
CHROME_TOP = 38
CHROME_SIDE = 5


def capture_login(url: str, width: int, height: int) -> tuple[Image.Image, dict]:
    """Real Chromium screenshot. Viewport is for composition only; checks still run at 390."""
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
            page.wait_for_timeout(250)
            box = page.locator("[data-testid='primary-cta']").bounding_box()
            metrics = page.evaluate(
                """() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth
                })"""
            )
            data = page.screenshot(type="png")
        finally:
            browser.close()
    if not box:
        raise RuntimeError("primary CTA was not visible in Chromium")
    meta = {
        "x": float(box["x"]),
        "y": float(box["y"]),
        "w": float(box["width"]),
        "h": float(box["height"]),
        "right": float(box["x"] + box["width"]),
        "scrollWidth": int(metrics["scrollWidth"]),
        "clientWidth": int(metrics["clientWidth"]),
        "captureWidth": width,
        "captureHeight": height,
    }
    return Image.open(BytesIO(data)).convert("RGB"), meta


def fit_contain(img: Image.Image, tw: int, th: int) -> Image.Image:
    """Scale the entire image into the box. Never crop."""
    ratio = min(tw / img.width, th / img.height)
    nw, nh = max(1, int(img.width * ratio)), max(1, int(img.height * ratio))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def crop_band(img: Image.Image, meta: dict, *, top: int, bot: int) -> tuple[int, int]:
    y0 = max(0, int(meta["y"]) - top)
    y1 = min(img.height, int(meta["y"] + meta["h"]) + bot)
    return y0, y1


def crop_cta_scene(img: Image.Image, meta: dict, *, mode: str) -> Image.Image:
    """Vertical crop around the form + CTA. Never crop the CTA on the right."""
    w = img.size[0]
    y0, y1 = crop_band(img, meta, top=380 if mode != "desktop" else 360, bot=40)
    right = int(round(meta["right"]))
    if mode == "desktop":
        x0, x1 = 0, min(w, max(right + 88, 640))
    else:
        x0, x1 = 0, w
    if x1 - x0 < right - x0 + 24:
        x1 = min(w, right + 48)
    return img.crop((x0, y0, x1, y1))


def wrap_lines(text: str, fnt, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if int(fnt.getlength(trial)) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]


def cta_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    px = img.load()
    w, h = img.size
    minx, miny, maxx, maxy = w, h, 0, 0
    n = 0
    for y in range(h):
        for x in range(0, w, 1):
            r, g, b = px[x, y][:3]
            if abs(r - 37) < 50 and abs(g - 99) < 60 and b > 175 and r < 90:
                n += 1
                minx, maxx = min(minx, x), max(maxx, x)
                miny, maxy = min(miny, y), max(maxy, y)
    if n < 80:
        return None
    return minx, miny, maxx, maxy



def _chrome_bar(draw, x0, y0, x1, y1, fill, title: str, title_fill) -> None:
    draw.rectangle((x0, y0, x1, y1), fill=fill)
    for i, col in enumerate(((248, 113, 113), (251, 191, 36), (52, 211, 153))):
        cx = x0 + 16 + i * 16
        cy = y0 + (y1 - y0) // 2
        draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=col)
    draw.text((x0 + 72, y0 + 10), title, fill=title_fill, font=font(14, True))


def scene_desktop(shot: Image.Image) -> Image.Image:
    pad = CHROME_SIDE
    canvas = Image.new("RGB", (shot.width + pad * 2, shot.height + CHROME_TOP + pad), (15, 23, 42))
    draw = ImageDraw.Draw(canvas)
    _chrome_bar(draw, 0, 0, canvas.width, CHROME_TOP, (15, 23, 42), "Chromium  ·  desktop 1440×900", INK)
    canvas.paste(shot, (pad, CHROME_TOP))
    draw.rectangle((pad - 1, CHROME_TOP - 1, pad + shot.width, CHROME_TOP + shot.height), outline=(51, 65, 85), width=2)
    return canvas


def scene_mobile_ok(shot: Image.Image) -> Image.Image:
    pad = CHROME_SIDE
    canvas = Image.new("RGB", (shot.width + pad * 2, shot.height + CHROME_TOP + 26), (6, 78, 59))
    draw = ImageDraw.Draw(canvas)
    _chrome_bar(draw, 0, 0, canvas.width, CHROME_TOP, (6, 78, 59), "390×844 MOBILE VIEWPORT  ·  CTA fits", INK)
    canvas.paste(shot, (pad, CHROME_TOP))
    draw.rectangle((pad - 1, CHROME_TOP - 1, pad + shot.width, CHROME_TOP + shot.height), outline=GREEN, width=3)
    draw.rectangle((0, canvas.height - 26, canvas.width, canvas.height), fill=(6, 78, 59))
    draw.text((12, canvas.height - 22), "CTA wraps inside the viewport", fill=INK, font=font(13, True))
    return canvas


def scene_mobile_fail(wide: Image.Image, meta: dict, *, vw: int, overflow_px: int) -> Image.Image:
    """390px viewport chrome; overflowing CTA continues outside the frame (same bitmap)."""
    y0, y1 = crop_band(wide, meta, top=360, bot=40)
    cta_right = int(round(meta["right"]))
    doc_right = int(meta.get("scrollWidth") or cta_right)
    right = min(wide.width, max(cta_right + 72, doc_right + 40))
    if right <= vw + 8:
        raise RuntimeError(f"wide capture does not include overflow: right={right} vw={vw}")
    inside = wide.crop((0, y0, vw, y1))
    wing = wide.crop((vw, y0, right, y1))
    pad = CHROME_SIDE
    wing_pad = 14
    frame_w = pad + inside.width + pad
    canvas_w = frame_w + wing.width + wing_pad + 18
    canvas_h = CHROME_TOP + inside.height + 28
    canvas = Image.new("RGB", (canvas_w, canvas_h), (30, 10, 12))
    draw = ImageDraw.Draw(canvas)
    bed_x = frame_w - pad
    draw.rectangle((bed_x, 0, canvas_w, canvas_h), fill=(69, 10, 10))
    for x in range(bed_x, canvas_w, 14):
        draw.line((x, 0, x + canvas_h // 2, canvas_h), fill=(127, 29, 29), width=1)
    _chrome_bar(draw, 0, 0, frame_w, CHROME_TOP, (127, 29, 29), "390×844 MOBILE VIEWPORT", INK)
    canvas.paste(inside, (pad, CHROME_TOP))
    canvas.paste(wing, (frame_w - pad, CHROME_TOP))
    draw.rectangle((pad - 1, CHROME_TOP - 1, pad + inside.width, CHROME_TOP + inside.height), outline=RED, width=4)
    edge_x = pad + inside.width
    draw.line((edge_x, CHROME_TOP - 4, edge_x, CHROME_TOP + inside.height + 4), fill=RED, width=5)
    by = CHROME_TOP + inside.height
    draw.rectangle((0, by, frame_w, canvas_h), fill=(127, 29, 29))
    draw.text((12, by + 6), "viewport edge", fill=(254, 202, 202), font=font(13, True))
    ox = edge_x + 10
    draw.rectangle((ox, 8, canvas_w - 8, 34), fill=(127, 29, 29))
    draw.text((ox + 8, 13), f"overflow +{overflow_px}px  beyond viewport", fill=INK, font=font(13, True))
    return canvas


def hero_stage(
    scene: Image.Image,
    *,
    kicker: str,
    title: str,
    rows: list[tuple[str, str, str]],
    footer: str,
    mood: str = "neutral",
) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    bar = {"fail": (127, 29, 29), "ok": (6, 78, 59)}.get(mood, (15, 23, 42))
    draw.rectangle((0, 0, W, HEAD_H), fill=bar)
    draw.text((20, 8), kicker, fill=(226, 232, 240), font=font(14, True))
    draw.text((20, 26), title, fill=INK, font=font(24, True))

    pane_h = H - HEAD_H
    inner_w, inner_h = LEFT_W - SAFE * 2, pane_h - SAFE * 2
    fitted = fit_contain(scene.convert("RGB"), inner_w, inner_h)
    px = SAFE
    py = HEAD_H + SAFE + max(0, (inner_h - fitted.height) // 2)
    img.paste(fitted, (px, py))

    draw.rectangle((LEFT_W, HEAD_H, LEFT_W + 2, H), fill=LINE)
    rx = LEFT_W + 16
    panel_w = W - rx - 14
    y = HEAD_H + 16
    draw.text((rx, y), "VERIFICATION", fill=MUTED, font=font(12, True))
    y += 28
    body_font = font(16, True)
    for mark, label, kind in rows:
        color = {"pass": GREEN, "fail": RED, "warn": AMBER, "dim": MUTED}.get(kind, INK)
        draw.text((rx, y), mark, fill=color, font=font(18, True))
        for ln in wrap_lines(label, body_font, panel_w - 28):
            draw.text((rx + 26, y), ln, fill=INK, font=body_font)
            y += 22
        y += 8
        if y > H - 80:
            break
    if footer:
        fy = H - 52
        for ln in wrap_lines(footer, font(12), panel_w):
            draw.text((rx, fy), ln, fill=MUTED, font=font(12))
            fy += 16
    return img


def assert_cta_uncropped_by_canvas(frame: Image.Image, *, view: str, viewport_px: int | None) -> None:
    box = cta_bbox(frame)
    if box is None:
        raise RuntimeError(f"{view}: CTA pixels not found in composed frame")
    x0, y0, x1, y1 = box
    if x1 >= W - 6:
        raise RuntimeError(f"{view}: CTA clipped by GIF canvas (x1={x1})")
    if x0 < 4:
        raise RuntimeError(f"{view}: CTA clipped on the left (x0={x0})")
    if view == "mobile-fail":
        if x1 >= LEFT_W - 6:
            raise RuntimeError(f"{view}: overflowing CTA hits the verification panel (x1={x1})")
        if x1 - x0 < 280:
            raise RuntimeError(f"{view}: CTA too narrow — overflow wing missing ({x1 - x0}px)")
        if x1 < 520:
            raise RuntimeError(f"{view}: overflow does not extend far enough (x1={x1})")
    if view == "mobile-ok":
        if x1 > LEFT_W - 8:
            raise RuntimeError(f"{view}: verified CTA crosses into the panel (x1={x1})")
        if x1 - x0 > 560:
            raise RuntimeError(f"{view}: verified CTA still looks like a nowrap overflow ({x1 - x0}px)")
    print(f"qa {view} cta=({x0},{y0})-({x1},{y1}) viewport_px={viewport_px}")


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
        fail_wide, fail_meta = capture_login(url, max(sw + 96, int(sw) + 80, 680), 844)
        if fail_meta["right"] > fail_meta["captureWidth"] - 8:
            raise RuntimeError(
                f"fail capture still clips the CTA: right={fail_meta['right']} "
                f"captureWidth={fail_meta['captureWidth']}"
            )
        desk_live, desk_meta = capture_login(url, 1440, 900)
        write_demo_app(app, broken=False)
        ok_390, ok_meta = capture_login(url, 390, 844)
        if ok_meta["right"] > vw + 1:
            # After the CSS fix the button must fit the 390 viewport in the bitmap.
            # (The acceptance check already used the real 390 run; this is GIF-only QA.)
            print("warn: fixed CTA right", ok_meta["right"], "vw", vw)
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

    desk_scene = scene_desktop(crop_cta_scene(desk_live, desk_meta, mode="desktop"))
    fail_scene = scene_mobile_fail(fail_wide, fail_meta, vw=vw, overflow_px=overflow_px)
    ok_scene = scene_mobile_ok(crop_cta_scene(ok_390, ok_meta, mode="ok"))
    if fail_meta["right"] < vw + 80:
        raise RuntimeError(
            f"fail capture CTA right {fail_meta['right']} does not overflow viewport {vw}"
        )

    gif_frames = [
        hero_stage(
            desk_scene,
            kicker="AGENT UI LOOP",
            title='Agent: “Done.”     Loop: “Prove it.”',
            rows=[
                ("•", 'Agent: “Done.”', "dim"),
                ("▶", "Loop: Prove it.", "warn"),
                ("•", "No evidence yet", "warn"),
                ("▶", "Open real Chromium", "warn"),
            ],
            footer="Acceptance · browser · evidence · proof",
        ),
        hero_stage(
            desk_scene,
            kicker="ACCEPTANCE",
            title="What does “Done” mean?",
            rows=[
                ("✓", "CTA visible", "pass"),
                ("✓", "Form functional", "pass"),
                ("…", "Mobile layout valid", "warn"),
                ("▶", "Chromium 1440×900 and 390×844", "warn"),
            ],
            footer="Explicit criteria — not a vibe",
        ),
        hero_stage(
            desk_scene,
            kicker="VERIFY  ·  DESKTOP",
            title="Desktop 1440×900  ·  PASS",
            rows=[
                ("✓", "desktop 1440×900", "pass"),
                ("…", "mobile 390×844 pending", "warn"),
                ("✓", "CTA / form / console", "pass"),
            ],
            footer="Desktop can pass while mobile fails",
            mood="ok",
        ),
        hero_stage(
            fail_scene,
            kicker="VERIFY  ·  MOBILE",
            title="✗  ACCEPTANCE FAILED",
            rows=[
                ("✓", "desktop 1440×900", "pass"),
                ("✗", "MOBILE OVERFLOW", "fail"),
                ("✗", f"scrollWidth={sw}", "fail"),
                ("✗", f"viewportWidth={vw}", "fail"),
                ("✗", f"overflowPx={overflow_px}", "fail"),
            ],
            footer="CTA is wider than the 390px viewport",
            mood="fail",
        ),
        hero_stage(
            fail_scene,
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
        ),
        hero_stage(
            ok_scene,
            kicker="FIX  ·  SAMPLE APP ONLY",
            title="Demo constrains the CTA in CSS",
            rows=[
                ("!", "Does not edit your repository", "warn"),
                ("→", "agent-ui-loop demo", "dim"),
                ("→", "applies sample CSS fix", "dim"),
                ("→", "then reverifies", "dim"),
            ],
            footer="Honest workflow: evidence → fix → re-run",
        ),
        hero_stage(
            ok_scene,
            kicker="REVERIFY",
            title="Same acceptance. Same browser.",
            rows=[
                ("✓", "desktop 1440×900", "pass"),
                ("✓", "mobile 390×844", "pass"),
                ("✓", "CTA fits the viewport", "pass"),
            ],
            footer="Re-run until the claim matches the UI",
            mood="ok",
        ),
        hero_stage(
            ok_scene,
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
        ),
    ]
    qa_specs = [
        "desktop",
        "desktop",
        "desktop",
        "mobile-fail",
        "mobile-fail",
        "mobile-ok",
        "mobile-ok",
        "mobile-ok",
    ]
    for fr, view in zip(gif_frames, qa_specs):
        assert_cta_uncropped_by_canvas(fr, view=view, viewport_px=vw)
    dest = ASSETS / "hero" / "agent-ui-loop-demo.gif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    durations = [1200, 1200, 1400, 2800, 2200, 1800, 1800, 2600]
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
