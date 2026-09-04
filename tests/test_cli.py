from pathlib import Path

from click.testing import CliRunner

from agent_ui_loop.cli import main


def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "prove" in result.output
    assert "demo" in result.output


def test_init_writes_config(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["init", "--url", "http://127.0.0.1:9999"])
        assert result.exit_code == 0
        text = Path("agent-ui-loop.yml").read_text(encoding="utf-8")
        assert "http://127.0.0.1:9999" in text
        assert "no-horizontal-overflow" in text


def test_init_refuses_overwrite(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("agent-ui-loop.yml").write_text("url: http://localhost:3000\n", encoding="utf-8")
        result = runner.invoke(main, ["init"])
        assert result.exit_code != 0


def test_run_missing_config(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["run"])
        assert result.exit_code == 2
        assert "why:" in result.output
        assert "fix:" in result.output


def test_prove_without_run(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["prove"])
        assert result.exit_code == 2
        assert "no verification run" in result.output


def test_malformed_config_cli(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("agent-ui-loop.yml").write_text("url: [\n", encoding="utf-8")
        result = runner.invoke(main, ["run"])
        assert result.exit_code == 2
        assert "malformed YAML" in result.output
