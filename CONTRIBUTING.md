# Contributing

Thanks for helping AI coding agents **prove** that a UI actually passed its acceptance criteria.

```
WRITE → RUN → VERIFY → EVIDENCE → FIX → REVERIFY → PROVE
```

This is not a SaaS, dashboard, visual-regression cloud, or UI generator.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
pytest
agent-ui-loop demo
```

## Where to contribute

| Area | Path | What to add |
| --- | --- | --- |
| Checks | `checks/`, `src/agent_ui_loop/checks/` | Deterministic measurements with evidence |
| Adapters | `adapters/` | Docs for invoking the CLI from an agent |
| Examples | `examples/` | Runnable contracts against a real page |
| Contracts | `contracts/` | Copyable YAML using the current schema |
| Docs | `docs/`, README | Accuracy over slogans |

Keep the YAML small. Measure something real. Fail closed.

See [checks/README.md](checks/README.md) and [docs/acceptance-contract.md](docs/acceptance-contract.md).

## Process

1. Open an issue if the change is a new check type (so we can keep the schema tight).
2. Add tests that use fixture HTML + Chromium when the check claims to observe a page.
3. Do not stub Playwright away for those checks.
4. Send a PR with what changed and how you ran it.

No CLA, no issue-template maze. Be kind; be specific.

## Not a fit

- Marketplaces / plugin stores
- Cloud backends that upload screenshots by default
- Subjective design auto-editors
- Giant E2E DSLs
- Fake screenshots or invented proof fields
