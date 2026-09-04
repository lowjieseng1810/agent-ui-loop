"""Tiny explicit journeys: fill / click / visible / wait. Not an E2E framework."""

from __future__ import annotations

from typing import Any

from agent_ui_loop.checks.base import CheckContext, result
from agent_ui_loop.config import Journey, Requirement
from agent_ui_loop.report import utc_now


def run_journey(journey: Journey, ctx: CheckContext) -> dict[str, Any]:
    req = Requirement("journey")
    observations: list[dict[str, Any]] = []
    page = ctx.page
    try:
        for i, step in enumerate(journey.steps):
            if step.action == "fill":
                page.fill(step.selector or "", step.value or "")
                observations.append({"step": i, "action": "fill", "selector": step.selector})
            elif step.action == "click":
                page.click(step.selector or "")
                try:
                    page.wait_for_load_state("load", timeout=5000)
                except Exception:
                    page.wait_for_timeout(150)
                observations.append({"step": i, "action": "click", "selector": step.selector})
            elif step.action == "wait":
                ms = min(max(step.ms or 100, 0), 5000)
                page.wait_for_timeout(ms)
                observations.append({"step": i, "action": "wait", "ms": ms})
            elif step.action == "visible":
                loc = page.locator(step.selector or "").first
                visible = loc.is_visible()
                observations.append(
                    {"step": i, "action": "visible", "selector": step.selector, "visible": visible}
                )
                if not visible:
                    outcome = result(
                        req,
                        ctx,
                        "failed",
                        {"journey": journey.name, "observations": observations},
                        f"journey {journey.name}: not visible {step.selector}",
                        why="An explicit user journey in the contract must complete.",
                    )
                    payload = outcome.to_dict()
                    payload["check"] = "journey"
                    payload["timestamp"] = utc_now()
                    return payload
    except Exception as exc:
        outcome = result(
            req,
            ctx,
            "failed",
            {"journey": journey.name, "observations": observations, "error": str(exc).split("\n")[0]},
            f"journey {journey.name} failed: {str(exc).split(chr(10))[0]}",
            why="An explicit user journey in the contract must complete.",
        )
        payload = outcome.to_dict()
        payload["check"] = "journey"
        payload["timestamp"] = utc_now()
        return payload
    outcome = result(
        req,
        ctx,
        "passed",
        {"journey": journey.name, "observations": observations},
        f"journey {journey.name} completed",
        why="An explicit user journey in the contract must complete.",
    )
    payload = outcome.to_dict()
    payload["check"] = "journey"
    payload["timestamp"] = utc_now()
    return payload
