"""Small, human-readable YAML acceptance contract. No code execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from agent_ui_loop.errors import UserError

DEFAULT_CONFIG_NAME = "agent-ui-loop.yml"
KNOWN_REQUIREMENT_TYPES = frozenset(
    {
        "element-visible",
        "element-exists",
        "no-horizontal-overflow",
        "no-console-errors",
        "no-network-failures",
        "no-broken-images",
        "element-in-viewport",
        "no-clipping",
    }
)
TYPES_REQUIRING_SELECTOR = frozenset(
    {"element-visible", "element-exists", "element-in-viewport"}
)


@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int


@dataclass(frozen=True)
class Requirement:
    type: str
    selector: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Config:
    url: str
    routes: list[str]
    viewports: list[Viewport]
    requirements: list[Requirement]
    timeout_ms: int = 15000
    headed: bool = False
    output_dir: str = ".agent-ui-loop"
    source_path: Path | None = None

    def absolute_url(self, route: str) -> str:
        base = self.url.rstrip("/")
        if route.startswith("http://") or route.startswith("https://"):
            return route
        if not route.startswith("/"):
            route = "/" + route
        return base + route


def default_config_text(url: str = "http://localhost:3000") -> str:
    return f"""# Agent UI Loop — acceptance contract
# REQUIRE → RUN → VERIFY → EVIDENCE → FIX → PROVE

url: {url}

routes:
  - /

viewports:
  - name: desktop
    width: 1440
    height: 900
  - name: mobile
    width: 390
    height: 844

requirements:
  - type: element-visible
    selector: "[data-testid='primary-cta']"
  - type: no-horizontal-overflow
  - type: no-console-errors
  - type: no-network-failures
  - type: no-broken-images
"""


def load_config(path: Path, url_override: str | None = None) -> Config:
    if not path.exists():
        raise UserError(
            what=f"config file not found: {path}",
            why="Agent UI Loop needs an acceptance contract before it can verify a UI.",
            fix=f"run `agent-ui-loop init` or pass --config pointing at an existing {DEFAULT_CONFIG_NAME}",
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise UserError(
            what=f"malformed YAML in {path}",
            why=str(exc).split("\n")[0],
            fix="fix the YAML syntax, then re-run. The schema is documented in the README.",
        ) from exc
    if raw is None:
        raise UserError(
            what=f"{path} is empty",
            why="an acceptance contract must declare at least a url.",
            fix="run `agent-ui-loop init` to write a starter config.",
        )
    if not isinstance(raw, dict):
        raise UserError(
            what=f"{path} must be a YAML mapping",
            why=f"got {type(raw).__name__}",
            fix="use the schema in the README (url, routes, viewports, requirements).",
        )
    return parse_config(raw, source_path=path, url_override=url_override)


def parse_config(
    raw: dict[str, Any],
    source_path: Path | None = None,
    url_override: str | None = None,
) -> Config:
    url = url_override or raw.get("url")
    if not url or not isinstance(url, str):
        raise UserError(
            what="missing `url`",
            why="verification needs a running app to open in a real browser.",
            fix="set `url: http://localhost:3000` in the config or pass `--url`.",
        )
    _validate_url(url)

    timeout_ms = int(raw.get("timeout_ms", 15000))
    if timeout_ms < 1000 or timeout_ms > 120000:
        raise UserError(
            what="invalid timeout_ms",
            why="timeout must be between 1000 and 120000 milliseconds.",
            fix="use a practical navigation timeout such as 15000.",
        )

    routes = raw.get("routes") or ["/"]
    if not isinstance(routes, list) or not routes:
        raise UserError(
            what="invalid `routes`",
            why="routes must be a non-empty list of path strings.",
            fix="example: `routes: [/login]`",
        )
    clean_routes: list[str] = []
    for route in routes:
        if not isinstance(route, str) or not route.strip():
            raise UserError(
                what="invalid route entry",
                why="each route must be a string such as `/login`.",
                fix="remove empty or non-string route entries.",
            )
        clean_routes.append(route if route.startswith("/") or route.startswith("http") else "/" + route)

    viewports = _parse_viewports(raw.get("viewports"))
    requirements = _parse_requirements(raw.get("requirements"))

    headed = bool(raw.get("headed", False))
    output_dir = str(raw.get("output_dir", ".agent-ui-loop"))

    return Config(
        url=url.rstrip("/"),
        routes=clean_routes,
        viewports=viewports,
        requirements=requirements,
        timeout_ms=timeout_ms,
        headed=headed,
        output_dir=output_dir,
        source_path=source_path,
    )


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UserError(
            what=f"invalid URL scheme: {url!r}",
            why="only http and https URLs are opened. file:, javascript:, and data: are rejected.",
            fix="start a local server and use http://127.0.0.1:<port>.",
        )
    if not parsed.netloc:
        raise UserError(
            what=f"invalid URL: {url!r}",
            why="the URL is missing a host.",
            fix="use a full URL such as http://localhost:3000.",
        )


def _parse_viewports(raw: Any) -> list[Viewport]:
    if raw is None:
        return [
            Viewport("desktop", 1440, 900),
            Viewport("mobile", 390, 844),
        ]
    if not isinstance(raw, list) or not raw:
        raise UserError(
            what="invalid `viewports`",
            why="viewports must be a non-empty list.",
            fix="example: `{name: mobile, width: 390, height: 844}`",
        )
    out: list[Viewport] = []
    for item in raw:
        if not isinstance(item, dict):
            raise UserError(
                what="invalid viewport entry",
                why="each viewport must be a mapping with name, width, height.",
                fix="see the example in `agent-ui-loop init`.",
            )
        name = str(item.get("name") or "").strip()
        try:
            width = int(item["width"])
            height = int(item["height"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UserError(
                what="viewport is missing width/height",
                why="width and height must be integers (CSS pixels).",
                fix="example: `width: 390` and `height: 844`.",
            ) from exc
        if not name:
            name = f"{width}x{height}"
        if width < 200 or height < 200 or width > 4000 or height > 4000:
            raise UserError(
                what=f"unreasonable viewport {width}×{height}",
                why="viewports must be between 200 and 4000 CSS pixels.",
                fix="use desktop (1440×900) and mobile (390×844) unless you have a reason not to.",
            )
        out.append(Viewport(name=name, width=width, height=height))
    return out


def _parse_requirements(raw: Any) -> list[Requirement]:
    if raw is None:
        return [
            Requirement("no-console-errors"),
            Requirement("no-network-failures"),
            Requirement("no-horizontal-overflow"),
            Requirement("no-broken-images"),
        ]
    if not isinstance(raw, list):
        raise UserError(
            what="invalid `requirements`",
            why="requirements must be a list of `{type: ...}` mappings.",
            fix="see the README for the supported check types.",
        )
    out: list[Requirement] = []
    for item in raw:
        if not isinstance(item, dict) or "type" not in item:
            raise UserError(
                what="invalid requirement entry",
                why="each requirement needs a `type` field.",
                fix="example: `{type: no-horizontal-overflow}`",
            )
        rtype = str(item["type"]).strip()
        if rtype not in KNOWN_REQUIREMENT_TYPES:
            known = ", ".join(sorted(KNOWN_REQUIREMENT_TYPES))
            raise UserError(
                what=f"unknown requirement type: {rtype}",
                why="the MVP schema is intentionally small.",
                fix=f"use one of: {known}",
            )
        selector = item.get("selector")
        if selector is not None:
            selector = str(selector)
        if rtype in TYPES_REQUIRING_SELECTOR and not selector:
            raise UserError(
                what=f"{rtype} requires `selector`",
                why="the check cannot observe a required element without a CSS selector.",
                fix="add `selector: \"[data-testid='primary-cta']\"` (or another stable selector).",
            )
        extra = {k: v for k, v in item.items() if k not in {"type", "selector"}}
        out.append(Requirement(type=rtype, selector=selector, extra=extra))
    return out
