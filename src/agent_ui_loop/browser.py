"""Playwright Chromium runner. One browser per verification; viewports reuse it."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent_ui_loop.config import Viewport
from agent_ui_loop.errors import UserError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Capture:
    console: list[dict[str, Any]] = field(default_factory=list)
    network: list[dict[str, Any]] = field(default_factory=list)


class BrowserSession:
    def __init__(self, headed: bool = False) -> None:
        self.headed = headed
        self._playwright = None
        self._browser = None

    def __enter__(self) -> "BrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise UserError(
                what="Playwright is not installed",
                why="Agent UI Loop launches a real Chromium browser via Playwright.",
                fix="pip install agent-ui-loop && python -m playwright install chromium",
                exit_code=3,
            ) from exc
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=not self.headed)
        except Exception as first:
            _try_install_chromium()
            try:
                self._browser = self._playwright.chromium.launch(headless=not self.headed)
            except Exception as second:
                raise UserError(
                    what="Chromium is unavailable",
                    why=str(second).split("\n")[0],
                    fix="run `python -m playwright install chromium` (Linux CI: add `--with-deps`).",
                    exit_code=3,
                ) from first
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def open_page(self, viewport: Viewport, color_scheme: str | None = None):
        assert self._browser is not None
        kwargs = {
            "viewport": {"width": viewport.width, "height": viewport.height},
            "device_scale_factor": 1,
        }
        if color_scheme in {"light", "dark"}:
            kwargs["color_scheme"] = color_scheme
        context = self._browser.new_context(**kwargs)
        page = context.new_page()
        capture = Capture()

        def on_console(msg) -> None:
            try:
                text = msg.text
            except Exception:
                text = "<unreadable console message>"
            capture.console.append(
                {"type": msg.type, "text": text, "timestamp": _now()}
            )

        def on_page_error(err) -> None:
            capture.console.append(
                {"type": "pageerror", "text": str(err), "timestamp": _now()}
            )

        def on_response(response) -> None:
            try:
                url = response.url
                status = response.status
                rtype = response.request.resource_type
            except Exception:
                return
            if url.startswith("data:"):
                return
            capture.network.append(
                {
                    "url": url,
                    "status": status,
                    "resourceType": rtype,
                    "failed": False,
                    "timestamp": _now(),
                }
            )

        def on_request_failed(request) -> None:
            try:
                url = request.url
                rtype = request.resource_type
                err = request.failure
            except Exception:
                return
            capture.network.append(
                {
                    "url": url,
                    "status": None,
                    "resourceType": rtype,
                    "failed": True,
                    "error": err,
                    "timestamp": _now(),
                }
            )

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)
        return context, page, capture


def navigate(page, url: str, timeout_ms: int) -> None:
    from playwright.sync_api import Error, TimeoutError as PlaywrightTimeout

    try:
        page.goto(url, wait_until="load", timeout=timeout_ms)
    except PlaywrightTimeout as exc:
        raise UserError(
            what=f"navigation timed out: {url}",
            why=f"the page did not reach load within {timeout_ms}ms.",
            fix="confirm the app is running, or raise `timeout_ms` in the config.",
            exit_code=3,
        ) from exc
    except Error as exc:
        message = str(exc)
        if "ERR_CONNECTION_REFUSED" in message or "net::ERR_" in message:
            raise UserError(
                what=f"server unavailable: {url}",
                why="Chromium could not connect. The app is not listening, or the URL is wrong.",
                fix="start the frontend (`npm run dev`, etc.) then re-run Agent UI Loop.",
                exit_code=3,
            ) from exc
        raise UserError(
            what=f"navigation failed: {url}",
            why=message.split("\n")[0],
            fix="open the URL in a browser yourself, then retry.",
            exit_code=3,
        ) from exc


def _try_install_chromium() -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        return


def dump_logs(console: list[dict[str, Any]], network: list[dict[str, Any]]) -> tuple[str, str]:
    console_text = "\n".join(
        f"{e.get('timestamp','')} [{e.get('type')}] {e.get('text')}" for e in console
    )
    network_text = "\n".join(
        json.dumps(e, ensure_ascii=True) for e in network
    )
    return console_text + ("\n" if console_text else ""), network_text + ("\n" if network_text else "")
