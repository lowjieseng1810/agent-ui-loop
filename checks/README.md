# Adding a check

Checks are Python classes registered in `src/agent_ui_loop/checks/`.

Keep them:

- deterministic (DOM / network / console measurements)
- local (no upload)
- small (one concern)

A check receives a `CheckContext` (Playwright `page`, viewport, captured console/network, screenshot path) and returns a `CheckResult` with `status`, `evidence`, and `message`.

Do not replace measurements with LLM guesses.

## Supported types (MVP)

- `no-console-errors`
- `no-network-failures`
- `element-exists`
- `element-visible`
- `no-horizontal-overflow`
- `no-broken-images`
- `element-in-viewport`
- `no-clipping`

Framework-specific checks belong in a follow-up PR with tests and an example config under `examples/`.
