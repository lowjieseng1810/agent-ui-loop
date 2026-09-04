"""Human + agent-readable CLI output."""

from __future__ import annotations

import json
from typing import Any

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
DIM = "\033[2m"
BOLD = "\033[1m"


def _c(enabled: bool, color: str, text: str) -> str:
    if not enabled:
        return text
    return f"{color}{text}{RESET}"


def mark(status: str, color: bool) -> str:
    if status == "passed":
        return _c(color, GREEN, "✓")
    return _c(color, RED, "✗")


def print_run(report: dict[str, Any], *, color: bool = True, json_mode: bool = False) -> None:
    if json_mode:
        print(json.dumps(agent_summary(report), indent=2))
        return
    meta = report.get("meta") or {}
    print()
    task = meta.get("taskName") or "ui-acceptance"
    reqs = [r for r in (report.get("results") or [])]
    unique = {}
    for item in reqs:
        unique.setdefault(item.get("check"), []).append(item)
    print(_c(color, BOLD, "Agent UI Loop") + "  ·  require  ·  verify  ·  prove")
    print(f"{_c(color, DIM, 'task')}    {task}")
    print(f"{_c(color, DIM, 'url')}     {meta.get('url')}")
    print(f"{_c(color, DIM, 'run')}     {meta.get('runId')}")
    if meta.get("commit"):
        print(f"{_c(color, DIM, 'commit')}  {meta.get('commitShort') or meta.get('commit')}")
    print()
    print(f"VERIFYING {len(unique)} REQUIREMENT TYPE(S)  ·  adversarial invalidate-claim")
    print()

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in report.get("results") or []:
        vp = item.get("viewport") or {}
        key = (item.get("route") or "", vp.get("name") or "")
        grouped.setdefault(key, []).append(item)

    for (route, vp_name), items in grouped.items():
        vp = (items[0].get("viewport") or {}) if items else {}
        header = f"{route}  {vp_name} {vp.get('width')}×{vp.get('height')}"
        print(_c(color, BOLD, header))
        for item in items:
            print(f"  {mark(item.get('status'), color)}  {item.get('check')}")
            if item.get("status") != "passed":
                print(f"      {item.get('message')}")
                evidence = item.get("evidence") or {}
                interesting = {
                    k: evidence[k]
                    for k in (
                        "scrollWidth",
                        "viewportWidth",
                        "overflowPx",
                        "selector",
                        "errorCount",
                        "failureCount",
                        "brokenCount",
                    )
                    if k in evidence
                }
                if interesting:
                    print(f"      evidence: {json.dumps(interesting, ensure_ascii=True)}")
        print()

    failures = [r for r in report.get("results") or [] if r.get("status") != "passed"]
    if failures:
        print(_c(color, RED, f"RESULT: FAILED  ({len(failures)} check{'s' if len(failures) != 1 else ''})"))
        print()
        print("FAILURES (actionable / layer 1)")
        for item in failures:
            vp = item.get("viewport") or {}
            print(
                f"- {item.get('route')} @ {vp.get('name')} "
                f"{vp.get('width')}×{vp.get('height')} · {item.get('check')}"
            )
            print(f"  {item.get('message')}")
            if item.get("screenshot"):
                print(f"  screenshot: {item.get('screenshot')}")
    else:
        print(_c(color, GREEN, "RESULT: PASSED"))

    print()
    print(f"Evidence: {meta.get('runDir')}")
    print()
    print("--- agent-summary ---")
    print(json.dumps(agent_summary(report), indent=2))


def agent_summary(report: dict[str, Any]) -> dict[str, Any]:
    results = report.get("results") or []
    failures = [r for r in results if r.get("status") != "passed"]
    return {
        "status": report.get("status"),
        "taskName": (report.get("meta") or {}).get("taskName"),
        "schemaVersion": (report.get("meta") or {}).get("schemaVersion", 3),
        "runId": (report.get("meta") or {}).get("runId"),
        "runDir": (report.get("meta") or {}).get("runDir"),
        "commit": (report.get("meta") or {}).get("commit"),
        "adversarial": (report.get("meta") or {}).get("adversarial"),
        "failed": len(failures),
        "passed": sum(1 for r in results if r.get("status") == "passed"),
        "failures": [
            {
                "check": r.get("check"),
                "route": r.get("route"),
                "viewport": r.get("viewport"),
                "message": r.get("message"),
                "evidence": {
                    k: v
                    for k, v in (r.get("evidence") or {}).items()
                    if k
                    in {
                        "scrollWidth",
                        "viewportWidth",
                        "overflowPx",
                        "selector",
                        "errorCount",
                        "failureCount",
                        "brokenCount",
                        "playwrightVisible",
                        "intersectsViewport",
                        "exitCode",
                        "meanDelta",
                        "exists",
                        "status",
                    }
                },
                "screenshot": r.get("screenshot"),
                "actionable": r.get("actionable", True),
                "layer": r.get("layer", 1),
            }
            for r in failures
        ],
    }
