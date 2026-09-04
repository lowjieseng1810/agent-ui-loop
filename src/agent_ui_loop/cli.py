"""CLI: init, run/check, prove, demo. Agent-readable output is first-class."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click

from agent_ui_loop import __version__
from agent_ui_loop.config import DEFAULT_CONFIG_NAME, default_config_text, load_config
from agent_ui_loop.demo import demo_config, find_free_port, start_demo_server, write_demo_app
from agent_ui_loop.errors import UserError
from agent_ui_loop.output import print_run
from agent_ui_loop.proof import (
    build_proof,
    latest_run_dir,
    load_report,
    previous_run_dir,
    render_proof_text,
    write_proof,
)
from agent_ui_loop.runner import run_verification


def _color() -> bool:
    return sys.stdout.isatty()


def _fail(exc: UserError) -> None:
    click.echo(exc.format_cli(), err=True)
    raise SystemExit(exc.exit_code)


@click.group()
@click.version_option(__version__, prog_name="agent-ui-loop")
def main() -> None:
    """Agent UI Loop — your agent can code. Now make it prove the UI.

    REQUIRE → RUN → VERIFY → EVIDENCE → FIX → PROVE
    """


@main.command()
@click.option("--url", default="http://localhost:3000", show_default=True)
@click.option("--force", is_flag=True, help="overwrite an existing config file")
def init(url: str, force: bool) -> None:
    """Write agent-ui-loop.yml (the acceptance contract)."""
    path = Path.cwd() / DEFAULT_CONFIG_NAME
    if path.exists() and not force:
        raise click.ClickException(
            f"{path.name} already exists. Pass --force to overwrite."
        )
    path.write_text(default_config_text(url), encoding="utf-8")
    click.echo(f"wrote {path}")
    skill_src = Path(__file__).parent / "skill.md"
    skill_dest = Path.cwd() / ".claude" / "skills" / "agent-ui-loop" / "SKILL.md"
    if skill_src.exists() and (force or not skill_dest.exists()):
        skill_dest.parent.mkdir(parents=True, exist_ok=True)
        skill_dest.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")
        click.echo(f"wrote {skill_dest}")
    click.echo("next: start your app, then `agent-ui-loop run`")


@main.command(name="run")
@click.option("--url", default=None, help="override config url")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_NAME, show_default=True)
@click.option("--headed", is_flag=True, help="show the Chromium window")
@click.option("--json", "json_mode", is_flag=True, help="print only the agent summary JSON")
def run_cmd(url: str | None, config_path: str, headed: bool, json_mode: bool) -> None:
    """Open a real browser, verify requirements, collect evidence."""
    _execute_run(url, config_path, headed, json_mode)


@main.command(name="check")
@click.option("--url", default=None)
@click.option("--config", "config_path", default=DEFAULT_CONFIG_NAME, show_default=True)
@click.option("--headed", is_flag=True)
@click.option("--json", "json_mode", is_flag=True)
def check_cmd(url: str | None, config_path: str, headed: bool, json_mode: bool) -> None:
    """Alias for run."""
    _execute_run(url, config_path, headed, json_mode)


def _execute_run(url: str | None, config_path: str, headed: bool, json_mode: bool) -> None:
    try:
        config = load_config(Path(config_path), url_override=url)
        report = run_verification(config, headed=headed or None)
    except UserError as exc:
        _fail(exc)
    print_run(report, color=_color(), json_mode=json_mode)
    raise SystemExit(0 if report.get("status") == "passed" else 1)


@main.command()
@click.option("--run-dir", "run_dir", default=None, help="proof a specific run directory")
@click.option("--json", "json_mode", is_flag=True)
def prove(run_dir: str | None, json_mode: bool) -> None:
    """Print verification proof from the latest (or given) run. Never faked."""
    try:
        output_root = Path.cwd() / ".agent-ui-loop"
        directory = Path(run_dir) if run_dir else latest_run_dir(output_root)
        if directory is None:
            raise UserError(
                what="no verification run found",
                why="proof is generated from stored evidence, not from a claim.",
                fix="run `agent-ui-loop run` or `agent-ui-loop demo` first.",
            )
        report = load_report(directory)
        previous = None
        prev_dir = previous_run_dir(output_root, directory)
        if prev_dir is not None:
            try:
                previous = load_report(prev_dir)
            except UserError:
                previous = None
        proof = build_proof(report, previous)
        write_proof(directory, proof, render_proof_text(proof, color=False))
    except UserError as exc:
        _fail(exc)
    if json_mode:
        click.echo(json.dumps(proof, indent=2))
    else:
        click.echo(render_proof_text(proof, color=_color()), nl=False)
    raise SystemExit(0 if proof.get("verified") else 1)


@main.command()
@click.option("--json", "json_mode", is_flag=True)
def compare(json_mode: bool) -> None:
    """Show before/after between the last two runs."""
    try:
        output_root = Path.cwd() / ".agent-ui-loop"
        current = latest_run_dir(output_root)
        if current is None:
            raise UserError(
                what="no runs to compare",
                why="before/after needs at least one completed run.",
                fix="run verification twice (fail, then fix, then re-run).",
            )
        report = load_report(current)
        prev_dir = previous_run_dir(output_root, current)
        previous = load_report(prev_dir) if prev_dir else None
        proof = build_proof(report, previous)
    except UserError as exc:
        _fail(exc)
    if json_mode:
        click.echo(json.dumps(proof.get("previous"), indent=2))
        return
    click.echo(render_proof_text(proof, color=_color()), nl=False)


@main.command()
@click.option("--keep", is_flag=True, help="leave demo files under .agent-ui-loop/demo")
@click.option("--json", "json_mode", is_flag=True)
@click.option("--no-fix", is_flag=True, help="stop after the intentional failure")
def demo(keep: bool, json_mode: bool, no_fix: bool) -> None:
    """Run the killer story: login page, mobile CTA overflow, fix, re-verify, prove."""
    cwd = Path.cwd()
    output_root = cwd / ".agent-ui-loop"
    demo_root = output_root / "demo"
    if demo_root.exists():
        shutil.rmtree(demo_root)
    app_dir = write_demo_app(demo_root / "app", broken=True)
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    server = start_demo_server(app_dir, port)
    try:
        config = demo_config(url)
        if not json_mode:
            click.echo()
            click.echo("KILLER DEMO  ·  Agent UI Loop")
            click.echo("Agent says: “Login page is complete.”")
            click.echo(f"Opening real Chromium against {url}/login …")
            click.echo()
        try:
            before = run_verification(config, cwd=cwd)
        except UserError as exc:
            _fail(exc)
        if not json_mode:
            print_run(before, color=_color(), json_mode=False)
            click.echo("That failure is real: the CTA row is min-width 520px on a 390px viewport.")
        if no_fix:
            if json_mode:
                click.echo(json.dumps({"before": before}, indent=2))
            raise SystemExit(1 if before.get("status") != "passed" else 0)

        if not json_mode:
            click.echo()
            click.echo("Applying the CSS fix (min-width: 0; width: 100%) …")
        write_demo_app(app_dir, broken=False)
        try:
            after = run_verification(config, cwd=cwd)
        except UserError as exc:
            _fail(exc)
        if json_mode:
            click.echo(json.dumps({"before": before, "after": after}, indent=2))
        else:
            print_run(after, color=_color(), json_mode=False)
            output_root = cwd / ".agent-ui-loop"
            directory = latest_run_dir(output_root)
            if directory is not None:
                report = load_report(directory)
                prev = previous_run_dir(output_root, directory)
                previous = load_report(prev) if prev else before
                proof = build_proof(report, previous)
                click.echo(render_proof_text(proof, color=_color()), nl=False)
        if not keep:
            pass
        raise SystemExit(0 if after.get("status") == "passed" else 1)
    finally:
        server.shutdown()
        server.server_close()
