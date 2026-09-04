from __future__ import annotations

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement

FAILURE_STATUSES = range(400, 600)


def _ignored(url: str) -> bool:
    path = url.split("?", 1)[0].rstrip("/").lower()
    return path.endswith("favicon.ico") or path.endswith("favicon.png")


class NetworkFailuresCheck:
    type = "no-network-failures"

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        failures = []
        for entry in ctx.network:
            if _ignored(str(entry.get("url") or "")):
                continue
            if entry.get("failed"):
                failures.append(entry)
                continue
            status = entry.get("status")
            if isinstance(status, int) and status in FAILURE_STATUSES:
                failures.append(entry)
        if failures:
            return result(
                requirement,
                ctx,
                "failed",
                {"failureCount": len(failures), "failures": failures[:20]},
                f"{len(failures)} HTTP/network failure(s) on {ctx.route}",
            )
        return result(
            requirement,
            ctx,
            "passed",
            {"failureCount": 0, "requestCount": len(ctx.network)},
            "no HTTP/network failures",
        )
