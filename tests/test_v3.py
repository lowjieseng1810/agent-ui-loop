from pathlib import Path

import yaml

from agent_ui_loop.checks import describe_checks
from agent_ui_loop.config import parse_config
from agent_ui_loop.evidence import build_evidence_graph
from agent_ui_loop.proof import build_proof, render_github_markdown, requirement_totals
from agent_ui_loop.runner import run_verification


FIXTURES = Path(__file__).parent / "fixtures"


def _run(url: str, tmp_path: Path, raw: dict):
    payload = {"url": url, "output_dir": str(tmp_path / "out"), "timeout_ms": 15000, **raw}
    if "routes" not in payload:
        payload["routes"] = ["/"]
    if "viewports" not in payload:
        payload["viewports"] = [{"name": "mobile", "width": 390, "height": 844}]
    return run_verification(parse_config(payload), cwd=tmp_path)


def test_task_name_and_new_types_parse():
    cfg = parse_config(
        {
            "task": {"name": "login-page"},
            "url": "http://localhost:3000",
            "requirements": [
                {"type": "route-available"},
                {"type": "file-exists", "path": "README.md"},
                {"type": "command", "command": ["python", "-m", "pytest", "-q"]},
                {"type": "a11y-names"},
            ],
            "color_schemes": ["light", "dark"],
            "journeys": [
                {
                    "name": "go",
                    "route": "/login",
                    "steps": [{"action": "click", "selector": "button"}],
                }
            ],
        }
    )
    assert cfg.task_name == "login-page"
    assert cfg.color_schemes == ("light", "dark")
    assert cfg.journeys[0].name == "go"


def test_route_available_and_http_status(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "ok")
    report = _run(
        url,
        tmp_path,
        {
            "requirements": [
                {"type": "route-available"},
                {"type": "http-status", "path": "/", "expect": 200},
            ]
        },
    )
    types = {r["check"]: r["status"] for r in report["results"]}
    assert types["route-available"] == "passed"
    assert types["http-status"] == "passed"


def test_file_exists_and_command(tmp_path: Path, serve_dir):
    url = serve_dir(FIXTURES / "ok")
    (tmp_path / "marker.txt").write_text("x", encoding="utf-8")
    report = _run(
        url,
        tmp_path,
        {
            "requirements": [
                {"type": "file-exists", "path": "marker.txt"},
                {"type": "command", "command": ["python3", "-c", "raise SystemExit(0)"]},
            ]
        },
    )
    by = {r["check"]: r for r in report["results"]}
    assert by["file-exists"]["status"] == "passed"
    assert by["command"]["status"] == "passed"
    assert by["command"]["evidence"]["exitCode"] == 0


def test_command_rejects_shell_string(tmp_path: Path, serve_dir):
    url = serve_dir(FIXTURES / "ok")
    report = _run(
        url,
        tmp_path,
        {"requirements": [{"type": "command", "command": "rm -rf /"}]},
    )
    cmd = [r for r in report["results"] if r["check"] == "command"][0]
    assert cmd["status"] == "failed"


def test_a11y_names(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "ok")
    report = _run(url, tmp_path, {"requirements": [{"type": "a11y-names"}]})
    a11y = [r for r in report["results"] if r["check"] == "a11y-names"][0]
    assert a11y["status"] == "passed"


def test_journey_graph_and_github_proof(tmp_path: Path):
    from agent_ui_loop.demo import demo_config, find_free_port, start_demo_server, write_demo_app

    app = write_demo_app(tmp_path / "app", broken=False)
    port = find_free_port()
    server = start_demo_server(app, port)
    try:
        cfg = demo_config(f"http://127.0.0.1:{port}")
        report = run_verification(cfg, cwd=tmp_path)
    finally:
        server.shutdown()
        server.server_close()
    journeys = [r for r in report["results"] if r["check"] == "journey"]
    assert journeys
    assert journeys[0]["status"] == "passed"
    assert report["graph"]["schemaVersion"] == 3
    proof = build_proof(report)
    md = render_github_markdown(proof)
    assert "Agent UI Verification" in md
    assert proof["kind"] == "agent-completion-proof"
    assert (Path(report["meta"]["runDir"]) / "github.md").exists()
    assert (Path(report["meta"]["runDir"]) / "logs" / "console.log").exists()


def test_evidence_graph_and_totals():
    report = {
        "meta": {"taskName": "login-page", "runId": "x", "url": "http://x", "commit": "abc"},
        "results": [
            {
                "check": "no-console-errors",
                "status": "passed",
                "route": "/",
                "viewport": {"name": "desktop"},
            },
            {
                "check": "no-console-errors",
                "status": "failed",
                "route": "/",
                "viewport": {"name": "mobile"},
            },
        ],
    }
    graph = build_evidence_graph(report)
    kinds = {n["kind"] for n in graph["nodes"]}
    assert kinds >= {"task", "requirement", "check", "observation", "evidence", "verdict"}
    totals = requirement_totals(report["results"])
    assert totals["total"] == 1
    assert totals["failed"] == 1


def test_reference_compare(serve_dir, tmp_path: Path):
    url = serve_dir(FIXTURES / "ok")
    first = _run(url, tmp_path / "a", {"requirements": [{"type": "no-horizontal-overflow"}]})
    shot = Path(first["meta"]["runDir"]) / first["screenshots"][0]["path"]
    dest = tmp_path / "b" / "ref.png"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(shot.read_bytes())
    report = _run(
        url,
        tmp_path / "b",
        {
            "requirements": [{"type": "no-horizontal-overflow"}],
            "reference": {"image": "ref.png", "viewport": "mobile"},
        },
    )
    cmp_ = [r for r in report["results"] if r["check"] == "reference-compare"]
    assert cmp_
    assert "meanDelta" in cmp_[0]["evidence"]
    assert (Path(report["meta"]["runDir"]) / "screenshots" / "reference-diff.png").exists()


def test_registry_documents_checks():
    rows = describe_checks()
    types = {r["type"] for r in rows}
    assert "route-available" in types
    assert "a11y-names" in types
    assert "command" in types


def test_github_action_yaml():
    action = yaml.safe_load(Path(__file__).resolve().parents[1].joinpath("action.yml").read_text())
    assert action["runs"]["using"] == "composite"
    assert "comment" in action["inputs"]
    assert "verified" in action["outputs"]
    names = [s.get("name") for s in action["runs"]["steps"]]
    assert "Upload proof artifact" in names
