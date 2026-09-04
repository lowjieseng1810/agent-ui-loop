"""Proof artifact + terminal / GitHub proof. Auditable evidence, not cryptography."""

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


def _req_key(item: dict[str, Any]) -> tuple:
    return (item.get("check"), item.get("selector") or "")


def requirement_totals(results: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for item in results:
        groups.setdefault(_req_key(item), []).append(item)
    rows = []
    passed = 0
    failed = 0
    for (check, selector), items in groups.items():
        ok = all(i.get("status") == "passed" for i in items)
        if ok:
            passed += 1
        else:
            failed += 1
        rows.append(
            {
                "check": check,
                "selector": selector or None,
                "label": _label(str(check or "")),
                "status": "passed" if ok else "failed",
                "instances": len(items),
            }
        )
    return {"total": len(rows), "passed": passed, "failed": failed, "rows": rows}


def build_proof(report: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = report.get("meta") or {}
    results = report.get("results") or []
    failed_instances = [r for r in results if r.get("status") != "passed"]
    totals = requirement_totals(results)
    verified = report.get("status") == "passed" and totals["failed"] == 0
    rows = []
    for route in meta.get("routes") or []:
        route_results = [r for r in results if r.get("route") == route]
        pageish = [r for r in route_results if r.get("scope") != "run"]
        pool = pageish or route_results
        ok = bool(pool) and all(r.get("status") == "passed" for r in pool)
        rows.append({"label": "Route", "value": route, "status": "passed" if ok else "failed"})
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
    for item in totals["rows"]:
        label = item["label"]
        if item.get("selector"):
            label = f"{label} `{item['selector']}`"
        rows.append({"label": label, "value": "", "status": item["status"]})

    proof = {
        "kind": "agent-completion-proof",
        "schemaVersion": 3,
        "verified": verified,
        "status": "VERIFIED" if verified else "NOT VERIFIED",
        "disclaimer": "Auditable verification evidence, not a cryptographic proof.",
        "taskName": meta.get("taskName") or "ui-acceptance",
        "requirements": totals,
        "commit": meta.get("commit"),
        "commitShort": meta.get("commitShort"),
        "runId": meta.get("runId"),
        "runDir": meta.get("runDir"),
        "url": meta.get("url"),
        "rows": rows,
        "screenshots": [s.get("path") for s in report.get("screenshots") or []],
        "logs": ["logs/console.log", "logs/network.log"],
        "reportJson": str(Path(meta.get("runDir") or ".") / "report.json"),
        "failures": failed_instances,
        "adversarial": meta.get("adversarial"),
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
        return (item.get("check"), item.get("route"), vp.get("name"), item.get("selector"))

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
    totals = proof.get("requirements") or {}
    task = proof.get("taskName") or "ui-acceptance"
    lines = [
        _c(color, BOLD, "AGENT COMPLETION PROOF"),
        "────────────────────────────",
        f"Task:                  {task}",
        f"Requirements:          {totals.get('total', 0)}",
        f"Passed:                {totals.get('passed', 0)}",
        f"Failed:                {totals.get('failed', 0)}",
        "",
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
    for log in proof.get("logs") or []:
        lines.append(f"  {log}")
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
    lines.append("Commit:")
    lines.append(f"  {commit}")
    lines.append("")
    lines.append("Proof means auditable evidence, not cryptography.")
    lines.append("")
    if proof.get("verified"):
        lines.append(_c(color, GREEN, "RESULT: VERIFIED ✓"))
    else:
        lines.append(_c(color, RED, "RESULT: NOT VERIFIED"))
    return "\n".join(lines) + "\n"


def render_github_markdown(proof: dict[str, Any]) -> str:
    totals = proof.get("requirements") or {}
    task = proof.get("taskName") or "ui-acceptance"
    n = totals.get("total", 0)
    p = totals.get("passed", 0)
    flag = "VERIFIED ✓" if proof.get("verified") else "NOT VERIFIED"
    lines = [
        "## Agent UI Verification",
        "",
        f"**Task:** {task}",
        f"**{p}/{n} requirements passed**",
        "",
    ]
    for row in proof.get("rows") or []:
        mark = "✓" if row.get("status") == "passed" else "✗"
        value = f" {row.get('value')}" if row.get("value") else ""
        lines.append(f"- {row.get('label')}{value}  {mark}")
    lines += [
        "",
        "**Evidence:**",
    ]
    for shot in proof.get("screenshots") or []:
        lines.append(f"- `{shot}`")
    commit = proof.get("commitShort") or proof.get("commit") or "unavailable"
    lines += [
        "",
        f"**Commit:** `{commit}`",
        "",
        f"**RESULT: {flag}**",
        "",
        "_Auditable verification evidence, not a cryptographic proof._",
        "",
    ]
    return "\n".join(lines)


def write_proof(run_dir: Path, proof: dict[str, Any], text: str) -> None:
    write_json(run_dir / "proof.json", proof)
    body = _strip_ansi(text)
    (run_dir / "proof.md").write_text("# Agent Completion Proof\n\n```\n" + body + "```\n", encoding="utf-8")
    (run_dir / "proof.txt").write_text(body, encoding="utf-8")
    (run_dir / "github.md").write_text(render_github_markdown(proof), encoding="utf-8")


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
        "a11y-names": "Accessible names",
        "a11y-contrast": "Contrast",
        "http-status": "HTTP status",
        "route-available": "Route available",
        "file-exists": "File exists",
        "command": "Test command",
        "reference-compare": "Reference comparison",
        "journey": "Journey",
    }.get(check, check)
