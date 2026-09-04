"""Run acceptance checks in a real browser and persist evidence locally."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from agent_ui_loop.browser import BrowserSession, dump_logs, navigate
from agent_ui_loop.checks import run_requirement
from agent_ui_loop.checks.base import CheckContext
from agent_ui_loop.config import Config, Viewport
from agent_ui_loop.errors import UserError
from agent_ui_loop.evidence import build_evidence_graph
from agent_ui_loop.gitutil import current_commit, short_commit
from agent_ui_loop.journeys import run_journey
from agent_ui_loop.proof import build_proof, previous_run_dir, render_proof_text, write_proof
from agent_ui_loop.report import render_report_md, utc_now, write_json
from agent_ui_loop.visual import resolve_provider


def slug(value: str) -> str:
    value = value.strip("/") or "root"
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
    return value[:80] or "root"


def new_run_id() -> str:
    stamp = utc_now().replace(":", "").replace("-", "")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def _append(results: list[dict[str, Any]], payload: dict[str, Any], commit: str | None) -> None:
    payload.setdefault("timestamp", utc_now())
    if commit:
        payload.setdefault("commit", commit)
    results.append(payload)


def run_verification(
    config: Config,
    *,
    cwd: Path | None = None,
    headed: bool | None = None,
) -> dict[str, Any]:
    cwd = cwd or Path.cwd()
    output_root = (cwd / config.output_dir).resolve()
    run_id = new_run_id()
    run_dir = output_root / "runs" / run_id
    shot_dir = run_dir / "screenshots"
    log_dir = run_dir / "logs"
    shot_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    commit = current_commit(cwd)
    started = utc_now()
    results: list[dict[str, Any]] = []
    screenshots: list[dict[str, Any]] = []
    all_console: list[dict[str, Any]] = []
    all_network: list[dict[str, Any]] = []
    visual_findings: list[dict[str, Any]] = []

    use_headed = config.headed if headed is None else headed
    visual = resolve_provider(None)
    schemes = list(config.color_schemes) or [None]
    first_vp = config.viewports[0]

    try:
        with BrowserSession(headed=use_headed) as session:
            for route in config.routes:
                url = config.absolute_url(route)
                for viewport in config.viewports:
                    for scheme in schemes:
                        context, page, capture = session.open_page(viewport, color_scheme=scheme)
                        try:
                            navigate(page, url, config.timeout_ms)
                            page.wait_for_timeout(150)
                            scheme_bit = f"--{scheme}" if scheme else ""
                            shot_name = f"{viewport.name}--{slug(route)}{scheme_bit}.png"
                            shot_path = shot_dir / shot_name
                            try:
                                page.screenshot(path=str(shot_path), full_page=False)
                            except Exception as exc:
                                raise UserError(
                                    what=f"screenshot failed ({viewport.name} {route})",
                                    why=str(exc).split("\n")[0],
                                    fix="confirm Chromium can write to .agent-ui-loop/ and the page rendered.",
                                    exit_code=3,
                                ) from exc
                            rel_shot = f"screenshots/{shot_name}"
                            screenshots.append(
                                {
                                    "route": route,
                                    "viewport": viewport.name,
                                    "colorScheme": scheme,
                                    "path": rel_shot,
                                }
                            )
                            ctx = CheckContext(
                                route=route,
                                url=url,
                                viewport=viewport,
                                console=capture.console,
                                network=capture.network,
                                screenshot=rel_shot,
                                measurements={},
                                page=page,
                                cwd=cwd,
                                run_dir=run_dir,
                                color_scheme=scheme,
                                screenshots=screenshots,
                            )
                            for requirement in config.page_requirements():
                                outcome = run_requirement(requirement, ctx)
                                _append(results, outcome.to_dict(), commit)
                            for journey in config.journeys:
                                if journey.route != route:
                                    continue
                                if journey.viewport and journey.viewport != viewport.name:
                                    continue
                                _append(results, run_journey(journey, ctx), commit)
                            for finding in visual.analyze(
                                shot_path, {"route": route, "viewport": viewport.name}
                            ):
                                visual_findings.append(finding.to_dict())
                            all_console.extend(
                                {**e, "route": route, "viewport": viewport.name} for e in capture.console
                            )
                            all_network.extend(
                                {**e, "route": route, "viewport": viewport.name} for e in capture.network
                            )
                        finally:
                            context.close()
    except Exception as exc:
        if not (run_dir / "report.json").exists():
            shutil.rmtree(run_dir, ignore_errors=True)
        if isinstance(exc, UserError):
            raise
        raise UserError(
            what="verification run crashed",
            why=str(exc).split("\n")[0],
            fix="re-run with a simpler page. If this persists, file an issue with report.json.",
            exit_code=3,
        ) from exc

    run_ctx = CheckContext(
        route=config.routes[0],
        url=config.absolute_url(config.routes[0]),
        viewport=first_vp,
        console=all_console,
        network=all_network,
        screenshot=screenshots[0]["path"] if screenshots else "",
        measurements={},
        page=None,
        cwd=cwd,
        run_dir=run_dir,
        color_scheme=None,
        screenshots=screenshots,
    )
    for requirement in config.run_requirements():
        if requirement.type == "route-available":
            for route in config.routes:
                ctx = CheckContext(
                    route=route,
                    url=config.absolute_url(route),
                    viewport=first_vp,
                    console=[],
                    network=[],
                    screenshot="",
                    measurements={},
                    page=None,
                    cwd=cwd,
                    run_dir=run_dir,
                    screenshots=screenshots,
                )
                _append(results, run_requirement(requirement, ctx).to_dict(), commit)
            continue
        _append(results, run_requirement(requirement, run_ctx).to_dict(), commit)

    failed = any(r.get("status") != "passed" for r in results)
    status = "failed" if failed else "passed"
    meta = {
        "schemaVersion": 3,
        "runId": run_id,
        "runDir": str(run_dir),
        "taskName": config.task_name,
        "url": config.url,
        "origin": _origin(config.url),
        "routes": config.routes,
        "viewports": [
            {"name": v.name, "width": v.width, "height": v.height} for v in config.viewports
        ],
        "colorSchemes": list(config.color_schemes),
        "requirementTypes": [r.type for r in config.requirements],
        "startedAt": started,
        "finishedAt": utc_now(),
        "commit": commit,
        "commitShort": short_commit(cwd),
        "status": status,
        "headed": use_headed,
        "configPath": str(config.source_path) if config.source_path else None,
        "networkPolicy": "local-first; screenshots and source are not uploaded",
        "adversarial": {
            "mode": "invalidate-completion-claim",
            "attempted": len(results),
            "invalidated": sum(1 for r in results if r.get("status") != "passed"),
        },
    }
    console_text, network_text = dump_logs(all_console, all_network)
    (run_dir / "console.log").write_text(console_text, encoding="utf-8")
    (run_dir / "network.log").write_text(network_text, encoding="utf-8")
    (log_dir / "console.log").write_text(console_text, encoding="utf-8")
    (log_dir / "network.log").write_text(network_text, encoding="utf-8")
    write_json(run_dir / "run-meta.json", meta)

    report = {
        "status": status,
        "meta": meta,
        "results": results,
        "screenshots": screenshots,
        "visualFindings": visual_findings,
        "policy": {
            "layer1": "deterministic — auto-actionable",
            "layer2": "visual reasoning — suggest only",
            "layer3": "subjective design — human review, never auto-fix",
        },
    }
    report["graph"] = build_evidence_graph(report)
    write_json(run_dir / "report.json", report)
    (run_dir / "report.md").write_text(render_report_md(report), encoding="utf-8")
    write_json(run_dir / "graph.json", report["graph"])

    prev_dir = previous_run_dir(output_root, run_dir)
    previous = None
    if prev_dir is not None:
        try:
            previous = json.loads((prev_dir / "report.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = None
    proof = build_proof(report, previous)
    text = render_proof_text(proof, color=False)
    write_proof(run_dir, proof, text)

    write_json(
        output_root / "latest.json",
        {"runId": run_id, "runDir": str(run_dir), "status": status, "taskName": config.task_name},
    )
    return report
