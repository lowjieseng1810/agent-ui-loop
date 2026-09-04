from __future__ import annotations

import subprocess
from pathlib import Path

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement

ALLOWED_BINS = frozenset({"pytest", "python", "python3", "npm", "npx", "node", "pnpm", "yarn"})


class CommandCheck:
    type = "command"
    description = "Run an existing test/build command and capture the result. No shell."
    domain = "test"
    scope = "run"
    why = "Existing tests are part of completion proof when the contract asks for them."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        raw = (requirement.extra or {}).get("command")
        if isinstance(raw, str):
            return result(
                requirement,
                ctx,
                "failed",
                {"command": raw},
                "command must be a YAML list, not a shell string",
                why=self.why,
            )
        if not isinstance(raw, list) or not raw or not all(isinstance(x, (str, int)) for x in raw):
            return result(
                requirement,
                ctx,
                "failed",
                {"command": raw},
                "command must be a non-empty argv list",
                why=self.why,
            )
        argv = [str(x) for x in raw]
        bin_name = Path(argv[0]).name
        if bin_name not in ALLOWED_BINS:
            return result(
                requirement,
                ctx,
                "failed",
                {"command": argv, "bin": bin_name},
                f"command binary {bin_name!r} is not allowlisted",
                why=self.why,
            )
        cwd = ctx.cwd or Path.cwd()
        timeout = int((requirement.extra or {}).get("timeout_s") or 60)
        timeout = max(1, min(timeout, 120))
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            return result(
                requirement,
                ctx,
                "failed",
                {"command": argv},
                f"executable not found: {argv[0]}",
                why=self.why,
                command=" ".join(argv),
            )
        except subprocess.TimeoutExpired:
            return result(
                requirement,
                ctx,
                "failed",
                {"command": argv, "timeout_s": timeout},
                f"command timed out after {timeout}s",
                why=self.why,
                command=" ".join(argv),
            )
        stdout = (proc.stdout or "")[-4000:]
        stderr = (proc.stderr or "")[-4000:]
        evidence = {
            "command": argv,
            "exitCode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        if proc.returncode != 0:
            return result(
                requirement,
                ctx,
                "failed",
                evidence,
                f"command exited {proc.returncode}: {' '.join(argv)}",
                why=self.why,
                command=" ".join(argv),
            )
        return result(
            requirement,
            ctx,
            "passed",
            evidence,
            f"command exited 0: {' '.join(argv)}",
            why=self.why,
            command=" ".join(argv),
        )
