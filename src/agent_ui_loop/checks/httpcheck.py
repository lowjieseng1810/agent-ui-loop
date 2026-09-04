from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement


class RouteAvailableCheck:
    type = "route-available"
    description = "GET the route and require an HTTP success status."
    domain = "runtime"
    scope = "run"
    why = "A completed page must actually load."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        url = ctx.url
        status, err = _http(url, method="GET")
        expect_max = 399
        ok = status is not None and status <= expect_max
        evidence = {"url": url, "status": status, "error": err}
        if not ok:
            return result(
                requirement,
                ctx,
                "failed",
                evidence,
                f"route unavailable: {url} status={status} {err or ''}".strip(),
                why=self.why,
            )
        return result(requirement, ctx, "passed", evidence, f"route available ({status})", why=self.why)


class HttpStatusCheck:
    type = "http-status"
    description = "Configurable HTTP request status check against the app origin."
    domain = "http"
    scope = "run"
    why = "API/page completion claims should match real HTTP status."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        extra = requirement.extra or {}
        path = str(extra.get("path") or extra.get("url") or ctx.route or "/")
        method = str(extra.get("method") or "GET").upper()
        if method not in {"GET", "HEAD"}:
            return result(
                requirement,
                ctx,
                "failed",
                {"method": method},
                f"http-status only allows GET/HEAD (got {method})",
                why=self.why,
            )
        expect = int(extra.get("expect") or extra.get("status") or 200)
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            origin = ctx.url.rsplit(ctx.route, 1)[0] if ctx.route and ctx.route != "/" else ctx.url
            # Prefer the configured absolute URL on the context
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(ctx.url)
            origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")
            url = origin + (path if path.startswith("/") else "/" + path)
        status, err = _http(url, method=method)
        evidence = {"url": url, "method": method, "status": status, "expect": expect, "error": err}
        if status != expect:
            return result(
                requirement,
                ctx,
                "failed",
                evidence,
                f"{method} {url} expected {expect} got {status}",
                why=self.why,
            )
        return result(requirement, ctx, "passed", evidence, f"{method} {url} → {status}", why=self.why)


def _http(url: str, method: str = "GET") -> tuple[int | None, str | None]:
    try:
        req = Request(url, method=method)
        with urlopen(req, timeout=8) as resp:
            return int(resp.status), None
    except HTTPError as exc:
        return int(exc.code), str(exc.reason)
    except URLError as exc:
        return None, str(exc.reason)
    except Exception as exc:
        return None, str(exc).split("\n")[0]
