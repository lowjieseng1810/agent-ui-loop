from pathlib import Path

import pytest

from agent_ui_loop.config import parse_config, load_config
from agent_ui_loop.errors import UserError


def test_parse_minimal_defaults():
    cfg = parse_config({"url": "http://localhost:3000"})
    assert cfg.routes == ["/"]
    assert len(cfg.viewports) == 2
    assert cfg.viewports[1].width == 390
    assert any(r.type == "no-horizontal-overflow" for r in cfg.requirements)


def test_parse_full_example():
    cfg = parse_config(
        {
            "url": "http://localhost:3000",
            "routes": ["login"],
            "viewports": [
                {"name": "desktop", "width": 1440, "height": 900},
                {"name": "mobile", "width": 390, "height": 844},
            ],
            "requirements": [
                {"type": "element-visible", "selector": "[data-testid='primary-cta']"},
                {"type": "no-horizontal-overflow"},
                {"type": "no-console-errors"},
            ],
        }
    )
    assert cfg.routes == ["/login"]
    assert cfg.absolute_url("/login") == "http://localhost:3000/login"
    assert cfg.requirements[0].selector == "[data-testid='primary-cta']"


def test_rejects_file_url():
    with pytest.raises(UserError) as exc:
        parse_config({"url": "file:///tmp/index.html"})
    assert "scheme" in exc.value.what.lower() or "invalid URL" in exc.value.what


def test_rejects_javascript_url():
    with pytest.raises(UserError):
        parse_config({"url": "javascript:alert(1)"})


def test_unknown_requirement_type():
    with pytest.raises(UserError) as exc:
        parse_config({"url": "http://localhost:3000", "requirements": [{"type": "pretty-please"}]})
    assert "unknown requirement" in exc.value.what


def test_element_visible_requires_selector():
    with pytest.raises(UserError) as exc:
        parse_config({"url": "http://localhost:3000", "requirements": [{"type": "element-visible"}]})
    assert "selector" in exc.value.what


def test_malformed_yaml(tmp_path: Path):
    path = tmp_path / "agent-ui-loop.yml"
    path.write_text("url: [unterminated\n", encoding="utf-8")
    with pytest.raises(UserError) as exc:
        load_config(path)
    assert "malformed YAML" in exc.value.what


def test_missing_config(tmp_path: Path):
    with pytest.raises(UserError):
        load_config(tmp_path / "missing.yml")


def test_invalid_viewport():
    with pytest.raises(UserError):
        parse_config(
            {"url": "http://localhost:3000", "viewports": [{"name": "tiny", "width": 10, "height": 10}]}
        )
