# Cursor adapter (thin)

Agent UI Loop is agent-agnostic. Cursor does not need a proprietary runner.

## Native / adapter / CLI-compatible

| Agent | Status |
| --- | --- |
| Claude Code | **Native** skill at `.claude/skills/agent-ui-loop/SKILL.md` |
| Cursor | **Adapter** — run the CLI; see this file |
| Codex | **CLI-compatible** — see `adapters/codex` |
| OpenCode | **CLI-compatible** — see `adapters/opencode` |

Core verification is never vendor-specific. Adapters only document how to invoke the CLI.

## Use

1. `pip install . && python -m playwright install chromium`
2. `agent-ui-loop init`
3. After UI edits, run `agent-ui-loop run` from the terminal or ask Cursor to run it.
4. Point the agent at `.agent-ui-loop/runs/<latest>/report.md` and the `--- agent-summary ---` JSON.
5. Fix layer-1 failures only, re-run, then `agent-ui-loop prove`.

## Rule snippet

You can paste this into a project rule:

```
After changing a web UI, run `agent-ui-loop run`.
Treat deterministic failures as blocking.
Do not claim the UI is done unless `agent-ui-loop prove` prints VERIFIED.
```

Do not put verification logic in Cursor-specific files. Extend checks in the core package.
