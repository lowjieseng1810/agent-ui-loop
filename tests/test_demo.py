from pathlib import Path

from click.testing import CliRunner

from agent_ui_loop.cli import main


def test_demo_end_to_end(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["demo", "--keep"])
        assert result.exit_code == 0, result.output
        assert "VERIFIED" in result.output or "PASSED" in result.output
        runs = list(Path(".agent-ui-loop/runs").iterdir())
        assert len(runs) >= 2
        latest = Path(".agent-ui-loop/latest.json")
        assert latest.exists()
        prove = runner.invoke(main, ["prove"])
        assert prove.exit_code == 0, prove.output
        assert "VERIFIED" in prove.output
