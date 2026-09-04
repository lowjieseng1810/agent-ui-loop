#!/usr/bin/env python3
"""Legacy GIF helper. Prefer: python scripts/build_release_assets.py"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from agent_ui_loop.demo import demo_config, find_free_port, start_demo_server, write_demo_app
from agent_ui_loop.runner import run_verification

W, H = 960, 540
CAPTION_H = 72


def font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def frame(title: str, body: Image.Image | None = None, subtitle: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), (17, 24, 39))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, CAPTION_H), fill=(15, 23, 42))
    draw.text((24, 18), title, fill=(248, 250, 252), font=font(22))
    if subtitle:
        draw.text((24, 44), subtitle, fill=(148, 163, 184), font=font(14))
    if body is not None:
        max_w, max_h = W - 80, H - CAPTION_H - 48
        ratio = min(max_w / body.width, max_h / body.height)
        nw, nh = max(1, int(body.width * ratio)), max(1, int(body.height * ratio))
        fitted = body.resize((nw, nh), Image.Resampling.LANCZOS)
        x = (W - nw) // 2
        y = CAPTION_H + (H - CAPTION_H - nh) // 2
        img.paste(fitted, (x, y))
    return img


def load_shot(run_dir: Path, name_prefix: str) -> Image.Image:
    shots = sorted((run_dir / "screenshots").glob(f"{name_prefix}*.png"))
    if not shots:
        raise SystemExit(f"missing screenshot {name_prefix} in {run_dir}")
    return Image.open(shots[0]).convert("RGB")


def main() -> None:
    root = Path.cwd()
    dest = root / "docs" / "demo.gif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = root / ".agent-ui-loop" / "gif-work"
    if work.exists():
        shutil.rmtree(work)
    app = write_demo_app(work / "app", broken=True)
    port = find_free_port(48731)
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

    before_dir = Path(before["meta"]["runDir"])
    after_dir = Path(after["meta"]["runDir"])
    mobile_fail = load_shot(before_dir, "mobile")
    desktop = load_shot(before_dir, "desktop")
    mobile_ok = load_shot(after_dir, "mobile")
    overflow = next(
        r
        for r in before["results"]
        if r["check"] == "no-horizontal-overflow" and r["status"] == "failed"
    )
    ev = overflow["evidence"]

    frames = [
        frame("Agent: “Login page is complete.”", subtitle="No evidence yet."),
        frame("Agent UI Loop · desktop 1440×900", desktop, "Chromium, real viewport"),
        frame("Agent UI Loop · mobile 390×844", mobile_fail, "CTA wider than the viewport"),
        frame(
            "Evidence: horizontal overflow",
            mobile_fail,
            f"scrollWidth={ev['scrollWidth']}  viewportWidth={ev['viewportWidth']}",
        ),
        frame("Agent fixes CSS", subtitle=".cta { width: 100%; min-width: 0; white-space: normal; }"),
        frame("Re-check · mobile", mobile_ok, "overflow gone"),
        frame("VERIFIED", mobile_ok, "Acceptance passed · proof written"),
    ]
    # Durations roughly match the README story (16s loop).
    durations = [2000, 2000, 2000, 2000, 3000, 3000, 2000]
    frames[0].save(
        dest,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
