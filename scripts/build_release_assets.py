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


def annotate_fail(shot: Image.Image, scroll: int, vw: int) -> Image.Image:
    img = shot.convert("RGB")
    # Crop to CTA area (lower-middle of 390x844)
    top = min(420, img.height - 280)
    crop = img.crop((0, top, img.width, min(img.height, top + 280)))
    canvas = Image.new("RGB", (crop.width, crop.height + 72), BG)
    canvas.paste(crop, (0, 72))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, canvas.width, 72), fill=(127, 29, 29))
    draw.text((16, 12), "✗  ACCEPTANCE FAILED", fill=INK, font=font(18, True))
    draw.text(
        (16, 40),
        f"Mobile 390×844  ·  overflow  scrollWidth={scroll}  viewportWidth={vw}",
        fill=(254, 202, 202),
        font=font(12),
    )
    return canvas


def before_after(before: Image.Image, after: Image.Image) -> Image.Image:
    def card(img, title, ok: bool):
        # Crop CTA band
        top = min(400, img.height - 360)
        crop = img.crop((0, top, img.width, min(img.height, top + 360))).resize((360, 332), Image.Resampling.LANCZOS)
        c = Image.new("RGB", (360, 380), PANEL)
        c.paste(crop, (0, 48))
        d = ImageDraw.Draw(c)
        color = GREEN if ok else RED
        d.rectangle((0, 0, 360, 48), fill=(20, 83, 45) if ok else (127, 29, 29))
        d.text((12, 14), title, fill=color, font=font(16, True))
        return c

    left = card(before, "BEFORE  ·  ✗ FAILED", False)
    right = card(after, "AFTER  ·  ✓ VERIFIED", True)
    canvas = Image.new("RGB", (760, 420), BG)
    canvas.paste(left, (16, 20))
    canvas.paste(right, (384, 20))
    return canvas


def proof_image(text: str) -> Image.Image:
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    canvas = Image.new("RGB", (920, 560), BG)
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (24, 24, 896, 536), 16, PANEL)
    y = 44
    draw.text((48, y), "AGENT COMPLETION PROOF", fill=INK, font=font(22, True))
    y = 88
    body = lines[:18]
    tail = [ln for ln in lines if ln.startswith("RESULT:") or ln.startswith("Proof means")]
    shown = body + ([""] if tail else []) + tail
    for ln in shown:
        color = INK
        if "VERIFIED" in ln:
            color = GREEN
        elif "NOT VERIFIED" in ln or (ln.startswith("Failed:") and not ln.endswith("0")):
            color = RED
        draw.text((48, y), ln[:90], fill=color, font=mono(13))
        y += 20
        if y > 500:
            break
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


def hero_static() -> Image.Image:
    img = Image.new("RGB", (1200, 640), BG)
    draw = ImageDraw.Draw(img)
    draw.text((56, 36), "AGENT UI LOOP", fill=MUTED, font=font(16, True))
    draw.text((56, 70), 'Agent: "Done."     Loop: "Prove it."', fill=INK, font=font(28, True))
    boxes = [
        (56, 160, "1  CLAIM", '"Login page is complete."', MUTED),
        (250, 160, "2  VERIFY", "Real Chromium  ·  1440 & 390", AMBER),
        (444, 160, "3  FAIL", "Mobile overflow caught", RED),
        (638, 160, "4  EVIDENCE", "screenshot + scrollWidth", INK),
        (832, 160, "5  FIX", "CSS constrained to viewport", MUTED),
        (1026, 160, "6  PROVE", "VERIFIED", GREEN),
    ]
    for x, y, title, body, color in boxes:
        rounded(draw, (x, y, x + 178, y + 280), 12, PANEL)
        draw.text((x + 14, y + 24), title, fill=color, font=font(13, True))
        # wrap body
        words = body.split()
        line, yy = "", y + 80
        for w in words:
            trial = (line + " " + w).strip()
            if font(14).getlength(trial) > 150:
                draw.text((x + 14, yy), line, fill=INK, font=font(14))
                line, yy = w, yy + 22
            else:
                line = trial
        if line:
            draw.text((x + 14, yy), line, fill=INK, font=font(14))
    rounded(draw, (56, 480, 1144, 590), 12, (6, 78, 59))
    draw.text((80, 512), "✓  VERIFIED", fill=GREEN, font=font(28, True))
    draw.text((80, 552), "Auditable evidence — screenshots, measurements, commit — not cryptography.", fill=INK, font=font(16))
    return img


def gif_frame(title: str, body: Image.Image | None, subtitle: str, *, fail=False, ok=False) -> Image.Image:
    img = Image.new("RGB", (960, 540), BG)
    draw = ImageDraw.Draw(img)
    bar = (127, 29, 29) if fail else ((6, 78, 59) if ok else PANEL)
    draw.rectangle((0, 0, 960, 88), fill=bar)
    draw.text((28, 18), title, fill=INK, font=font(24, True))
    draw.text((28, 52), subtitle, fill=(226, 232, 240), font=font(16))
    if body is not None:
        max_w, max_h = 880, 400
        ratio = min(max_w / body.width, max_h / body.height)
        nw, nh = max(1, int(body.width * ratio)), max(1, int(body.height * ratio))
        fitted = body.resize((nw, nh), Image.Resampling.LANCZOS)
        img.paste(fitted, ((960 - nw) // 2, 88 + (452 - nh) // 2))
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
        write_demo_app(app, broken=False)
        after = run_verification(cfg, cwd=work)
    finally:
        server.shutdown()
        server.server_close()

    bdir = Path(before["meta"]["runDir"])
    adir = Path(after["meta"]["runDir"])
    fail_shot = Image.open(next((bdir / "screenshots").glob("mobile*.png"))).convert("RGB")
    ok_shot = Image.open(next((adir / "screenshots").glob("mobile*.png"))).convert("RGB")
    desk = Image.open(next((bdir / "screenshots").glob("desktop*.png"))).convert("RGB")
    overflow = next(
        r
        for r in before["results"]
        if r["check"] == "no-horizontal-overflow" and r["status"] == "failed"
    )
    ev = overflow["evidence"]
    sw, vw = int(ev["scrollWidth"]), int(ev["viewportWidth"])

    proof_text = (adir / "proof.txt").read_text(encoding="utf-8")
    # Copy raw artifacts for docs
    raw = ROOT / "assets" / "examples"
    raw.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(adir / "proof.txt", ROOT / "docs" / "sample-proof.txt")
    shutil.copyfile(adir / "github.md", ROOT / "docs" / "sample-github-comment.md")
    shutil.copyfile(adir / "proof.json", raw / "proof.json")

    fail = annotate_fail(fail_shot, sw, vw)
    save(fail, ASSETS / "screenshots" / "mobile-failure.png")
    save(before_after(fail_shot, ok_shot), ASSETS / "screenshots" / "before-after.png")
    save(proof_image(proof_text), ASSETS / "screenshots" / "proof.png")
    save(social(), ASSETS / "social" / "github-social-preview.png")
    save(hero_static(), ASSETS / "hero" / "agent-ui-loop-hero.png")
    write_svg_loop(ASSETS / "diagrams" / "verification-loop.svg")
    write_svg_acceptance(ASSETS / "diagrams" / "acceptance-flow.svg")

    gif_frames = [
        gif_frame('Agent: “Done.”', None, "No evidence. Completion is a claim."),
        gif_frame("Agent UI Loop: Prove it.", desk, "Real Chromium  ·  desktop 1440×900  ·  pass", ok=True),
        gif_frame("✗  Mobile acceptance failed", fail, f"scrollWidth={sw}  viewportWidth={vw}", fail=True),
        gif_frame("Evidence captured", fail, "screenshot + DOM measurements  ·  not a guess", fail=True),
        gif_frame("Demo applies the CSS fix", None, "The demo workflow edits the sample app. It does not edit your repo."),
        gif_frame("Reverify  ·  mobile", ok_shot, "overflow gone  ·  CTA fits 390×844", ok=True),
        gif_frame("✓  VERIFIED", ok_shot, "AGENT COMPLETION PROOF written  ·  auditable evidence", ok=True),
    ]
    dest = ASSETS / "hero" / "agent-ui-loop-demo.gif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    durations = [900, 1400, 2800, 2000, 1800, 2000, 2800]
    gif_frames[0].save(
        dest,
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    shutil.copyfile(dest, ROOT / "docs" / "demo.gif")
    print("wrote", dest, file=sys.stderr)

    # stills for docs
    stills = ROOT / "docs" / "stills"
    stills.mkdir(parents=True, exist_ok=True)
    fail_shot.save(stills / "mobile-before.png")
    ok_shot.save(stills / "mobile-after.png")
    desk.save(stills / "desktop.png")

    meta = {
        "scrollWidth": sw,
        "viewportWidth": vw,
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
