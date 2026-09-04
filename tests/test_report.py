from agent_ui_loop.proof import build_proof, compare_runs, render_proof_text
from agent_ui_loop.report import render_report_md


def _report(status="failed"):
    return {
        "status": status,
        "meta": {
            "taskName": "login-page",
            "runId": "1",
            "runDir": "/tmp/run",
            "url": "http://127.0.0.1:9",
            "routes": ["/login"],
            "viewports": [{"name": "mobile", "width": 390, "height": 844}],
            "requirementTypes": ["no-horizontal-overflow"],
            "commit": "deadbeefcafebabe",
            "commitShort": "deadbee",
        },
        "results": [
            {
                "check": "no-horizontal-overflow",
                "status": "failed" if status == "failed" else "passed",
                "route": "/login",
                "viewport": {"name": "mobile", "width": 390, "height": 844},
                "message": "overflow",
                "screenshot": "screenshots/mobile.png",
                "evidence": {"scrollWidth": 520, "viewportWidth": 390},
                "layer": 1,
                "actionable": True,
            }
        ],
        "screenshots": [{"route": "/login", "viewport": "mobile", "path": "screenshots/mobile.png"}],
    }


def test_markdown_report_answers_the_four_questions():
    md = render_report_md(_report("failed"))
    assert "What was checked" in md
    assert "What failed" in md
    assert "What passed" in md
    assert "Evidence" in md
    assert "deadbeef" in md


def test_proof_not_verified_on_failure():
    proof = build_proof(_report("failed"))
    assert proof["verified"] is False
    text = render_proof_text(proof, color=False)
    assert "NOT VERIFIED" in text
    assert "AGENT COMPLETION PROOF" in text


def test_proof_verified_on_pass():
    proof = build_proof(_report("passed"))
    assert proof["verified"] is True
    assert "VERIFIED" in render_proof_text(proof, color=False)


def test_before_after_compare():
    before = _report("failed")
    after = _report("passed")
    changes = compare_runs(before, after)
    assert changes
    assert changes[0]["before"] == "failed"
    assert changes[0]["after"] == "passed"
