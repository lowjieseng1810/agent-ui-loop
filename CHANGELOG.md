# Changelog

## 0.3.0 — Agent UI Verification (current)

This is the public V3 slice: an acceptance contract, a real-browser verification run, evidence on disk, and an auditable completion proof.

### Current functionality

- CLI: `init`, `run` / `check`, `prove`, `compare`, `demo`
- Acceptance contract YAML (`agent-ui-loop.yml`) with routes, viewports, requirements, optional journeys
- Playwright Chromium checks for visibility, overflow, clipping, images, console, network, routes, HTTP status, file existence, allowlisted commands
- Optional checks: `a11y-names`, `a11y-contrast`, `reference-compare`, `color_schemes`
- Journeys: `fill`, `click`, `visible`, `wait`
- Evidence graph + `proof.json` / `proof.txt` / `proof.md` / `github.md` (`kind: agent-completion-proof`, schemaVersion 3)
- Built-in demo: real mobile CTA overflow → CSS fix of the **sample app** → reverify → VERIFIED
- Native Claude Code skill; Cursor adapter docs; Codex / OpenCode CLI compatibility
- Composite GitHub Action in this repository (`action.yml`) — use `uses: ./` after checkout

### Known limitations

- Not published on PyPI yet. Install from this repository: `pip install .`
- The Action is not a GitHub Marketplace listing. Copy `action.yml` usage from the README.
- Layer-2 visual reasoning is off and is not a working vision product in this release.
- Journeys are four primitives, not an E2E framework.
- `command` checks are argv-only and allowlisted; they are not a test runner replacement.
- Authentication, multi-page apps, and headed debugging beyond `--headed` are out of scope for the default contract.
- Proof is **auditable evidence, not cryptographic proof**.

### Experimental

- `a11y-contrast`, `reference-compare`, and dark/light `color_schemes` exist in the schema. Treat them as optional, not as a visual-regression product.

### Not in this release (ideas, not claims)

- PyPI publication
- Marketplace Action publication
- Automatic edits to **your** repository (the demo only patches its own sample CSS)
- Cloud backends, dashboards, or SaaS
