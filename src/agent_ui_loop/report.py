"""Evidence + Markdown/JSON reports. Local-only; nothing is uploaded."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def render_report_md(report: dict[str, Any]) -> str:
    meta = report.get("meta") or {}
    results = report.get("results") or []
    failed = [r for r in results if r.get("status") != "passed"]
    passed = [r for r in results if r.get("status") == "passed"]
    status = report.get("status", "unknown").upper()
    lines = [
        "# Agent UI Loop report",
        "",
        f"**Result:** {status}",
        f"**Run:** `{meta.get('runId', '')}`",
        f"**URL:** {meta.get('url', '')}",
        f"**Commit:** `{meta.get('commit') or 'unavailable'}`",
        f"**Started:** {meta.get('startedAt', '')}",
        "",
        "## What was checked",
        "",
        f"- Routes: {', '.join(f'`{r}`' for r in meta.get('routes') or [])}",
        f"- Viewports: {', '.join(_vp(v) for v in meta.get('viewports') or [])}",
        f"- Requirements: {', '.join(f'`{r}`' for r in meta.get('requirementTypes') or [])}",
        "",
        "## What failed",
        "",
    ]
    if not failed:
        lines.append("_Nothing failed._")
    else:
        for item in failed:
            lines.extend(_result_block(item))
    lines += ["", "## What passed", ""]
    if not passed:
        lines.append("_Nothing passed._")
    else:
        for item in passed:
            lines.append(
                f"- `{item.get('check')}` on `{item.get('route')}` "
                f"@ {_vp(item.get('viewport'))} — {item.get('message')}"
            )
    lines += ["", "## Evidence", ""]
    shots = report.get("screenshots") or []
    if shots:
        for shot in shots:
            rel = shot.get("path")
            lines.append(f"- {shot.get('viewport')} `{shot.get('route')}`: `{rel}`")
            lines.append(f"  ![]({rel})")
    else:
        lines.append("_No screenshots._")
    lines += ["", "## Proof pointers", ""]
    lines.append(f"- JSON: `report.json`")
    lines.append(f"- Markdown: `report.md`")
    if meta.get("commit"):
        lines.append(f"- Code version: `{meta['commit']}`")
    lines.append("")
    return "\n".join(lines)


def _vp(viewport: Any) -> str:
    if isinstance(viewport, dict):
        name = viewport.get("name") or ""
        w = viewport.get("width")
        h = viewport.get("height")
        if w and h:
            return f"{name} {w}×{h}".strip()
        return name
    return str(viewport)


def _result_block(item: dict[str, Any]) -> list[str]:
    evidence = item.get("evidence") or {}
    compact = {k: v for k, v in evidence.items() if k not in {"errors", "failures", "broken", "outside"}}
    lines = [
        f"### `{item.get('check')}` — {item.get('status')}",
        "",
        f"- Route: `{item.get('route')}`",
        f"- Viewport: {_vp(item.get('viewport'))}",
        f"- Message: {item.get('message')}",
        f"- Screenshot: `{item.get('screenshot')}`",
        f"- Layer: {item.get('layer')} ({'actionable' if item.get('actionable') else 'suggestion'})",
        f"- Measured: `{json.dumps(compact, ensure_ascii=True)}`",
        "",
    ]
    return lines


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
