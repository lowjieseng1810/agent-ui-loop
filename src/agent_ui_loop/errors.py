"""User-facing errors: WHAT / WHY / HOW TO FIX. No stack traces in normal CLI output."""

from __future__ import annotations


class UserError(Exception):
    def __init__(self, what: str, why: str, fix: str, exit_code: int = 2) -> None:
        super().__init__(what)
        self.what = what
        self.why = why
        self.fix = fix
        self.exit_code = exit_code

    def format_cli(self) -> str:
        return (
            f"error: {self.what}\n"
            f"  why:  {self.why}\n"
            f"  fix:  {self.fix}"
        )
