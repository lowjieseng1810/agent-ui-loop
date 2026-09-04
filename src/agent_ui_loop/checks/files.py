from __future__ import annotations

from pathlib import Path

from agent_ui_loop.checks.base import CheckContext, CheckResult, result
from agent_ui_loop.config import Requirement


class FileExistsCheck:
    type = "file-exists"
    description = "Require a repository-relative file to exist."
    domain = "code"
    scope = "run"
    why = "A completion claim about code should be checkable on disk."

    def run(self, requirement: Requirement, ctx: CheckContext) -> CheckResult:
        rel = str((requirement.extra or {}).get("path") or "")
        cwd = (ctx.cwd or Path.cwd()).resolve()
        target = (cwd / rel).resolve()
        try:
            target.relative_to(cwd)
        except ValueError:
            return result(
                requirement,
                ctx,
                "failed",
                {"path": rel},
                "file-exists path escaped the project directory",
                why=self.why,
            )
        exists = target.is_file()
        evidence = {"path": rel, "resolved": str(target), "exists": exists}
        if not exists:
            return result(requirement, ctx, "failed", evidence, f"missing file: {rel}", why=self.why)
        return result(requirement, ctx, "passed", evidence, f"file exists: {rel}", why=self.why)
