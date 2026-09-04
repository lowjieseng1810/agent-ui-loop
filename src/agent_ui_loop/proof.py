"""Proof artifact + terminal proof. Never faked: derived only from stored run reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_ui_loop.errors import UserError
from agent_ui_loop.output import GREEN, RESET, RED, BOLD, _c
from agent_ui_loop.report import write_json


def latest_run_dir(output_root: Path) -> Path | None:
    pointer = output_root / "latest.json"
    if pointer.exists():
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            path = Path(data["runDir"])
            if path.exists():
                return path
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    runs = output_root / "runs"
    if not runs.exists():
        return None
    dirs = sorted([p for p in runs.iterdir() if p.is_dir() and (p / "report.json").exists()])
    return dirs[-1] if dirs else None


def previous_run_dir(output_root: Path, current: Path) -> Path | None:
    runs = output_root / "runs"
    if not runs.exists():
        return None
    dirs = sorted([p for p in runs.iterdir() if p.is_dir() and (p / "report.json").exists()])
    try:
        idx = dirs.index(current)
    except ValueError:
        return dirs[-1] if dirs else None
    if idx <= 0:
        return None
    return dirs[idx - 1]


def load_report(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "report.json"
    if not path.exists():
        raise UserError(
            what=f"no report.json in {run_dir}",
            why="proof can only be generated from a completed verification run.",
            fix="run `agent-ui-loop run` first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_proof(report: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = report.get("meta") or {}
    results = report.get("results") or []
    failed = [r for r in results if r.get("status") != "passed"]
    verified = report.get("status") == "passed" and not failed
    rows = []
    seen_routes = []
    for route in meta.get("routes") or []:
        route_results = [r for r in results if r.get("route") == route]
        ok = bool(route_results) and all(r.get("status") == "passed" for r in route_results)
        rows.append({"label": "Route", "value": route, "status": "passed" if ok else "failed"})
        seen_routes.append(route)
    for vp in meta.get("viewports") or []:
        name = vp.get("name")
        related = [r for r in results if (r.get("viewport") or {}).get("name") == name]
        ok = bool(related) and all(r.get("status") == "passed" for r in related)
        rows.append(
            {
                "label": name.title() if name else "Viewport",
                "value": f"{vp.get('width')}×{vp.get('height')}",
                "status": "passed" if ok else "failed",
            }
        )
    by_check: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        by_check.setdefault(item.get("check") or "?", []).append(item)
    for check, items in by_check.items():
        ok = all(i.get("status") == "passed" for i in items)
        rows.append(
            {
                "label": _label(check),
                "value": "",
                "status": "passed" if ok else "failed",
            }
        )
    proof = {
        "kind": "agent-ui-proof",
        "verified": verified,
        "status": "VERIFIED" if verified else "NOT VERIFIED",
        "commit": meta.get("commit"),
        "commitShort": meta.get("commitShort"),
        "runId": meta.get("runId"),
        "runDir": meta.get("runDir"),
        "url": meta.get("url"),
        "rows": rows,
        "screenshots": [s.get("path") for s in report.get("screenshots") or []],
        "reportJson": str(Path(meta.get("runDir") or ".") / "report.json"),
        "failures": failed,
        "previous": None,
    }
    if previous:
        proof["previous"] = {
            "runId": (previous.get("meta") or {}).get("runId"),
            "status": previous.get("status"),
            "comparison": compare_runs(previous, report),
        }
    return proof


def compare_runs(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple:
        vp = item.get("viewport") or {}
        return (item.get("check"), item.get("route"), vp.get("name"))

    before_map = {key(i): i for i in before.get("results") or []}
    after_map = {key(i): i for i in after.get("results") or []}
    out = []
    for k, after_item in after_map.items():
        before_item = before_map.get(k)
        if before_item is None:
            continue
        if before_item.get("status") != after_item.get("status"):
            out.append(
                {
                    "check": after_item.get("check"),
                    "route": after_item.get("route"),
                    "viewport": after_item.get("viewport"),
                    "before": before_item.get("status"),
                    "after": after_item.get("status"),
                    "beforeMessage": before_item.get("message"),
                    "afterMessage": after_item.get("message"),
                    "beforeEvidence": before_item.get("evidence"),
                    "afterEvidence": after_item.get("evidence"),
                }
            )
    return out


def render_proof_text(proof: dict[str, Any], *, color: bool = True) -> str:
    lines = [
        _c(color, BOLD, "AGENT UI PROOF"),
        "────────────────────────────",
    ]
    for row in proof.get("rows") or []:
        flag = _c(color, GREEN, "✓") if row.get("status") == "passed" else _c(color, RED, "✗")
        label = f"{row.get('label'):<22}"
        value = f"{row.get('value')}"
        lines.append(f"{label}{value:<14}{flag}")
    lines.append("")
    lines.append("Evidence:")
    for shot in proof.get("screenshots") or []:
        lines.append(f"  {shot}")
    lines.append(f"  {proof.get('reportJson')}")
    lines.append("")
    prev = proof.get("previous")
    if prev and prev.get("comparison"):
        lines.append("Before / after:")
        for change in prev["comparison"]:
            vp = (change.get("viewport") or {}).get("name")
            lines.append(
                f"  {change.get('check')} @ {change.get('route')} {vp}: "
                f"{change.get('before')} → {change.get('after')}"
            )
        lines.append("")
    commit = proof.get("commitShort") or proof.get("commit") or "unavailable"
    lines.append(f"Commit:")
    lines.append(f"  {commit}")
    lines.append("")
    if proof.get("verified"):
        lines.append(_c(color, GREEN, "RESULT: VERIFIED ✓"))
    else:
        lines.append(_c(color, RED, "RESULT: NOT VERIFIED"))
    return "\n".join(lines) + "\n"


def write_proof(run_dir: Path, proof: dict[str, Any], text: str) -> None:
    write_json(run_dir / "proof.json", proof)
    (run_dir / "proof.md").write_text(
        "# Agent UI Proof\n\n```\n" + _strip_ansi(text) + "```\n",
        encoding="utf-8",
    )
    (run_dir / "proof.txt").write_text(_strip_ansi(text), encoding="utf-8")


def _strip_ansi(text: str) -> str:
    for code in (GREEN, RED, BOLD, RESET, "\033[2m"):
        text = text.replace(code, "")
    return text


def _label(check: str) -> str:
    return {
        "element-visible": "Primary element visible",
        "element-exists": "Required element exists",
        "no-horizontal-overflow": "No horizontal overflow",
        "no-broken-images": "No broken images",
        "no-console-errors": "No console errors",
        "no-network-failures": "No network failures",
        "element-in-viewport": "Element in viewport",
        "no-clipping": "No clipping",
    }.get(check, check)
