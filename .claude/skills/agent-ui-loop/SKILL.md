---
name: agent-ui-loop
description: >
  Prove that an implemented task actually meets its acceptance contract.
  UI-first: real browser, deterministic checks, evidence, then proof.
  Do not say "done" when agent-ui-loop.yml exists until verification passes.
---

# Agent UI Loop (V3)

AI coding agents should not just say "done". They should prove it.

REQUIRE → IMPLEMENT → VERIFY → READ EVIDENCE → FIX → REVERIFY → PROVE

## When to invoke

Whenever a UI (or UI-related) task is about to be declared complete, and
especially when `agent-ui-loop.yml` exists.

Do not declare completion without running verification if an acceptance
contract is present.

## What verified means

`agent-ui-loop prove` prints `RESULT: VERIFIED`. That is auditable evidence
(screenshots, measurements, logs, git commit), not cryptography.

## Contract

```bash
pip install .
python -m playwright install chromium
agent-ui-loop init --url http://localhost:3000
```

`agent-ui-loop.yml` stays small: `task`, `url`, `routes`, `viewports`, `requirements`.
Optional: `journeys`, `color_schemes`, `reference`, `http-status`, `command`,
`file-exists`, `a11y-names`. See `docs/acceptance-contract.md`.

## Commands

```bash
agent-ui-loop run            # adversarial: try to invalidate the completion claim
agent-ui-loop check          # alias of run
agent-ui-loop prove
agent-ui-loop compare
agent-ui-loop demo
agent-ui-loop run --json     # agent-only stdout
```

## Loop

1. Receive the task and the contract.
2. Implement the UI.
3. Start the app.
4. Run `agent-ui-loop run`.
5. Read FAILURES and `--- agent-summary ---`.
6. Fix only layer-1 deterministic failures using measurements and screenshots.
7. Re-run until pass.
8. `agent-ui-loop prove`. Only then say the task is complete.

## Layers

1. Deterministic (auto-actionable): overflow, visibility, console, HTTP, images, a11y names.
2. Visual reasoning (suggest): reference mismatch without a threshold.
3. Subjective design (human): never auto-change brand/aesthetics.

## Safe to fix

Layout overflow, missing required elements, console/network/broken images,
missing labels you introduced, failing allowlisted test commands in the contract.

Ask before deleting requirements, changing brand, or weakening the contract.

## Stop

Stop when proof is VERIFIED, or when the blocker is environmental (server down)
and you reported it with the CLI what/why/fix text.
