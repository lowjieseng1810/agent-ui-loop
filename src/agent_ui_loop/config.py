"""Small, human-readable YAML acceptance contract. No code execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from agent_ui_loop.errors import UserError

DEFAULT_CONFIG_NAME = "agent-ui-loop.yml"

PAGE_REQUIREMENT_TYPES = frozenset(
    {
        "element-visible",
        "element-exists",
        "no-horizontal-overflow",
        "no-console-errors",
        "no-network-failures",
        "no-broken-images",
        "element-in-viewport",
        "no-clipping",
        "a11y-names",
        "a11y-contrast",
    }
)
RUN_REQUIREMENT_TYPES = frozenset(
    {
        "http-status",
        "route-available",
        "file-exists",
        "command",
        "reference-compare",
    }
)
KNOWN_REQUIREMENT_TYPES = PAGE_REQUIREMENT_TYPES | RUN_REQUIREMENT_TYPES
TYPES_REQUIRING_SELECTOR = frozenset(
    {"element-visible", "element-exists", "element-in-viewport"}
)
CHECK_DOMAINS = {
    "element-visible": "ui",
    "element-exists": "ui",
    "no-horizontal-overflow": "ui",
    "no-console-errors": "runtime",
    "no-network-failures": "runtime",
    "no-broken-images": "ui",
    "element-in-viewport": "ui",
    "no-clipping": "ui",
    "a11y-names": "ui",
    "a11y-contrast": "ui",
    "http-status": "http",
    "route-available": "runtime",
    "file-exists": "code",
    "command": "test",
    "reference-compare": "ui",
}


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

    @property
    def domain(self) -> str:
        return CHECK_DOMAINS.get(self.type, "ui")

    @property
    def scope(self) -> str:
        return "run" if self.type in RUN_REQUIREMENT_TYPES else "page"


@dataclass(frozen=True)
class JourneyStep:
    action: str
    selector: str | None = None
    value: str | None = None
    ms: int | None = None


@dataclass(frozen=True)
class Journey:
    name: str
    route: str
    steps: tuple[JourneyStep, ...]
    viewport: str | None = None


@dataclass(frozen=True)
class ReferenceSpec:
    image: str
    route: str | None = None
    viewport: str | None = None
    max_diff_ratio: float | None = None


@dataclass(frozen=True)
class Config:
    url: str
    routes: list[str]
    viewports: list[Viewport]
    requirements: list[Requirement]
    task_name: str = "ui-acceptance"
    timeout_ms: int = 15000
    headed: bool = False
    output_dir: str = ".agent-ui-loop"
    color_schemes: tuple[str, ...] = ()
    journeys: tuple[Journey, ...] = ()
    reference: ReferenceSpec | None = None
    source_path: Path | None = None

    def absolute_url(self, route: str) -> str:
        base = self.url.rstrip("/")
        if route.startswith("http://") or route.startswith("https://"):
            return route
        if not route.startswith("/"):
            route = "/" + route
        return base + route

    def page_requirements(self) -> list[Requirement]:
        return [r for r in self.requirements if r.scope == "page"]

    def run_requirements(self) -> list[Requirement]:
        reqs = [r for r in self.requirements if r.scope == "run"]
        if self.reference is not None and not any(r.type == "reference-compare" for r in reqs):
            extra: dict[str, Any] = {
                "image": self.reference.image,
                "maxDiffRatio": self.reference.max_diff_ratio,
            }
            if self.reference.route:
                extra["route"] = self.reference.route
            if self.reference.viewport:
                extra["viewport"] = self.reference.viewport
            reqs.append(Requirement("reference-compare", extra=extra))
        return reqs


def default_config_text(url: str = "http://localhost:3000") -> str:
    return f"""# Agent UI Loop — acceptance contract (V3)
# REQUIRE → EXECUTE → VERIFY → EVIDENCE → FIX → RE-VERIFY → PROVE

task:
  name: ui-acceptance

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
  - type: route-available
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
            fix="fix the YAML syntax, then re-run. The schema is documented in docs/acceptance-contract.md.",
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
            fix="use the schema in docs/acceptance-contract.md (url, routes, viewports, requirements).",
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

    task = raw.get("task") or {}
    task_name = "ui-acceptance"
    if isinstance(task, dict) and task.get("name"):
        task_name = str(task["name"]).strip() or task_name
    elif isinstance(raw.get("task"), str):
        task_name = str(raw["task"]).strip() or task_name

    viewports = _parse_viewports(raw.get("viewports"))
    requirements = _parse_requirements(raw.get("requirements"))
    journeys = _parse_journeys(raw.get("journeys"))
    reference = _parse_reference(raw.get("reference"))
    color_schemes = _parse_color_schemes(raw.get("color_schemes") or raw.get("colorSchemes"))

    headed = bool(raw.get("headed", False))
    output_dir = str(raw.get("output_dir", ".agent-ui-loop"))

    return Config(
        url=url.rstrip("/"),
        routes=clean_routes,
        viewports=viewports,
        requirements=requirements,
        task_name=task_name,
        timeout_ms=timeout_ms,
        headed=headed,
        output_dir=output_dir,
        color_schemes=color_schemes,
        journeys=journeys,
        reference=reference,
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
            Requirement("route-available"),
        ]
    if not isinstance(raw, list):
        raise UserError(
            what="invalid `requirements`",
            why="requirements must be a list of `{type: ...}` mappings.",
            fix="see docs/acceptance-contract.md for supported check types.",
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
                why="the contract schema is intentionally small.",
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
        if rtype == "command" and not extra.get("command"):
            raise UserError(
                what="command requires `command`",
                why="test verification runs an existing command; it does not invent tests.",
                fix="example: `{type: command, command: [python, -m, pytest, -q]}`",
            )
        if rtype == "file-exists" and not extra.get("path"):
            raise UserError(
                what="file-exists requires `path`",
                why="the check needs a repository-relative file path.",
                fix="example: `{type: file-exists, path: app/login/page.tsx}`",
            )
        out.append(Requirement(type=rtype, selector=selector, extra=extra))
    return out


def _parse_journeys(raw: Any) -> tuple[Journey, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise UserError(
            what="invalid `journeys`",
            why="journeys must be a list of named step sequences.",
            fix="see docs/acceptance-contract.md. Keep journeys tiny: fill / click / visible.",
        )
    allowed = {"fill", "click", "visible", "wait"}
    out: list[Journey] = []
    for item in raw:
        if not isinstance(item, dict):
            raise UserError(
                what="invalid journey",
                why="each journey is a mapping with name, route, steps.",
                fix="example: `{name: sign-in, route: /login, steps: [...]}`",
            )
        name = str(item.get("name") or "journey").strip()
        route = str(item.get("route") or "/").strip()
        if not route.startswith("/"):
            route = "/" + route
        steps_raw = item.get("steps") or []
        if not isinstance(steps_raw, list) or not steps_raw:
            raise UserError(
                what=f"journey {name!r} has no steps",
                why="a journey must declare at least one fill/click/visible/wait step.",
                fix="keep the sequence short — this is not a full E2E DSL.",
            )
        steps: list[JourneyStep] = []
        for step in steps_raw:
            if not isinstance(step, dict) or "action" not in step:
                raise UserError(
                    what="invalid journey step",
                    why="each step needs `action`.",
                    fix="actions: fill, click, visible, wait.",
                )
            action = str(step["action"]).strip()
            if action not in allowed:
                raise UserError(
                    what=f"unknown journey action: {action}",
                    why="the journey DSL is intentionally tiny.",
                    fix="use fill, click, visible, or wait.",
                )
            selector = step.get("selector")
            if action in {"fill", "click", "visible"} and not selector:
                raise UserError(
                    what=f"{action} step requires selector",
                    why="the browser cannot act without a target.",
                    fix="add a CSS selector.",
                )
            ms = step.get("ms")
            steps.append(
                JourneyStep(
                    action=action,
                    selector=str(selector) if selector else None,
                    value=None if step.get("value") is None else str(step.get("value")),
                    ms=int(ms) if ms is not None else None,
                )
            )
        viewport = item.get("viewport")
        out.append(
            Journey(
                name=name,
                route=route,
                steps=tuple(steps),
                viewport=str(viewport) if viewport else None,
            )
        )
    return tuple(out)


def _parse_reference(raw: Any) -> ReferenceSpec | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return ReferenceSpec(image=raw)
    if not isinstance(raw, dict) or not raw.get("image"):
        raise UserError(
            what="invalid `reference`",
            why="reference needs `image: path/to.png`.",
            fix="this is evidence of difference, not a Percy clone.",
        )
    ratio = raw.get("maxDiffRatio", raw.get("max_diff_ratio"))
    return ReferenceSpec(
        image=str(raw["image"]),
        route=str(raw["route"]) if raw.get("route") else None,
        viewport=str(raw["viewport"]) if raw.get("viewport") else None,
        max_diff_ratio=float(ratio) if ratio is not None else None,
    )


def _parse_color_schemes(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise UserError(
            what="invalid `color_schemes`",
            why="must be a list such as `[light, dark]`.",
            fix="omit the field unless the app exposes prefers-color-scheme.",
        )
    allowed = {"light", "dark"}
    out: list[str] = []
    for item in raw:
        name = str(item).strip().lower()
        if name not in allowed:
            raise UserError(
                what=f"unknown color scheme: {item}",
                why="only light and dark are emulated via prefers-color-scheme.",
                fix="use `color_schemes: [light, dark]`.",
            )
        out.append(name)
    return tuple(out)
