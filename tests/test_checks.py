from __future__ import annotations

from pathlib import Path

import yaml

from agent_ui_loop.config import parse_config
from agent_ui_loop.proof import build_proof, load_report
from agent_ui_loop.runner import run_verification

FIXTURES = Path(__file__).parent / "fixtures"


def _run(url: str, tmp_path: Path, requirements, viewports=None):
    raw = {
        "url": url,
        "routes": ["/"],
        "viewports": viewports
        or [{"name": "mobile", "width": 390, "height": 844}],
        "requirements": requirements,
        "output_dir": str(tmp_path / "out"),
        "timeout_ms": 15000,
    }
    config = parse_config(raw)
    return run_verification(config, cwd=tmp_path)


def _statuses(report):
    return {(r["check"], r["status"]) for r in report["results"]}


def test_pass_case(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "ok")
    report = _run(
        url,
        tmp_path,
        [
            {"type": "element-visible", "selector": "[data-testid='primary-cta']"},
            {"type": "element-exists", "selector": "[data-testid='primary-cta']"},
            {"type": "no-horizontal-overflow"},
            {"type": "no-console-errors"},
            {"type": "no-network-failures"},
            {"type": "no-broken-images"},
            {"type": "element-in-viewport", "selector": "[data-testid='primary-cta']"},
        ],
        viewports=[
            {"name": "desktop", "width": 1440, "height": 900},
            {"name": "mobile", "width": 390, "height": 844},
        ],
    )
    assert report["status"] == "passed"
    assert Path(report["meta"]["runDir"], "report.json").exists()
    assert Path(report["meta"]["runDir"], "report.md").exists()
    assert Path(report["meta"]["runDir"], "screenshots").exists()
    shots = list(Path(report["meta"]["runDir"], "screenshots").glob("*.png"))
    assert shots
    proof = build_proof(report)
    assert proof["verified"] is True


def test_overflow_fail_and_evidence(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "overflow")
    report = _run(url, tmp_path, [{"type": "no-horizontal-overflow"}])
    assert report["status"] == "failed"
    overflow = report["results"][0]
    assert overflow["check"] == "no-horizontal-overflow"
    assert overflow["status"] == "failed"
    evidence = overflow["evidence"]
    assert evidence["scrollWidth"] > evidence["viewportWidth"]
    assert evidence["viewportWidth"] == 390


def test_console_error_detection(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "console")
    report = _run(url, tmp_path, [{"type": "no-console-errors"}])
    assert report["status"] == "failed"
    errors = report["results"][0]["evidence"]["errors"]
    assert any("boom-from-page" in (e.get("text") or "") for e in errors)


def test_http_failure_detection(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "http-fail")
    report = _run(url, tmp_path, [{"type": "no-network-failures"}])
    assert report["status"] == "failed"
    assert report["results"][0]["evidence"]["failureCount"] >= 1


def test_element_exists_and_visible(serve_dir, tmp_path: Path):
    missing = _run(
        serve_dir(FIXTURES / "missing"),
        tmp_path / "missing",
        [{"type": "element-exists", "selector": "[data-testid='primary-cta']"}],
    )
    assert missing["status"] == "failed"
    hidden = _run(
        serve_dir(FIXTURES / "hidden"),
        tmp_path / "hidden",
        [{"type": "element-visible", "selector": "[data-testid='primary-cta']"}],
    )
    assert hidden["status"] == "failed"


def test_broken_images(serve_dir, tmp_path: Path):
    report = _run(serve_dir(FIXTURES / "broken-image"), tmp_path, [{"type": "no-broken-images"}])
    assert report["status"] == "failed"
    assert report["results"][0]["evidence"]["brokenCount"] >= 1


def test_server_unavailable(tmp_path: Path):
    from agent_ui_loop.errors import UserError
    import pytest

    with pytest.raises(UserError) as exc:
        _run("http://127.0.0.1:1", tmp_path, [{"type": "no-console-errors"}])
    assert exc.value.exit_code == 3
    assert "unavailable" in exc.value.what.lower() or "unavailable" in exc.value.why.lower()
    runs = tmp_path / "out" / "runs"
    if runs.exists():
        incomplete = [p for p in runs.iterdir() if p.is_dir() and not (p / "report.json").exists()]
        assert incomplete == []


def test_report_and_proof_files(serve_dir, tmp_path: Path):
    report = _run(
        serve_dir(FIXTURES / "ok"),
        tmp_path,
        [{"type": "no-horizontal-overflow"}],
    )
    run_dir = Path(report["meta"]["runDir"])
    loaded = load_report(run_dir)
    assert loaded["status"] == "passed"
    md = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "What was checked" in md
    assert (run_dir / "proof.json").exists()
    assert (run_dir / "console.log").exists()
    assert (run_dir / "network.log").exists()
    assert (run_dir / "run-meta.json").exists()


def test_example_yaml_matches_supported_schema():
    example = Path(__file__).resolve().parents[1] / "examples" / "agent-ui-loop.yml"
    raw = yaml.safe_load(example.read_text(encoding="utf-8"))
    cfg = parse_config(raw)
    assert cfg.routes
