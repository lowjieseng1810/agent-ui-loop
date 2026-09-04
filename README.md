# Agent UI Loop

## Your agent can code. Now make it prove the UI.

![Agent UI Loop demo: mobile CTA overflow detected, fixed, then verified](docs/demo.gif)

Agent UI Loop gives AI coding agents a real-browser verification loop for frontend interfaces: **verify requirements, collect evidence, fix failures, and prove the result.**

An agent should not merely say “Done.”
It should be able to prove: **“Done — and here is the evidence.”**

```bash
pip install agent-ui-loop
python -m playwright install chromium
agent-ui-loop demo
```

No sample app to prepare. The demo ships a login page with a **real** mobile CTA overflow, catches it with Playwright, applies the CSS fix, re-checks, and prints `VERIFIED`.

```
REQUIRE  →  RUN  →  VERIFY  →  EVIDENCE  →  FIX  →  PROVE
```

Built for developers using **Claude Code**, Cursor, Codex, and OpenCode on React / Next.js / plain HTML. Claude Code is first-class (`.claude/skills/agent-ui-loop`); the core is agent-agnostic.

---

## Why this exists

AI coding agents generate frontends quickly. Code completion does **not** guarantee that the rendered UI:

- fits the viewport
- works on mobile
- contains the required elements
- has no console failures
- has no obvious layout failures
- satisfies explicit UI acceptance requirements

Today a human still has to open the browser and nag the agent. Agent UI Loop turns that into a repeatable, agent-native loop.

This is **not** “AI makes prettier websites,” visual QA theater, screenshot tourism, or a Percy/Chromatic clone.

**Acceptance-driven UI verification with evidence.**

---

## Install

```bash
pip install agent-ui-loop
python -m playwright install chromium
```

Chromium is required. The CLI will try to install it on first launch if it is missing; CI should run `python -m playwright install chromium --with-deps`.

---

## Quick start on your app

```bash
agent-ui-loop init --url http://localhost:3000
# start your UI
agent-ui-loop run
agent-ui-loop prove
```

### Acceptance contract

`agent-ui-loop.yml` is the product. Keep it small.

```yaml
url: http://localhost:3000
routes:
  - /login
viewports:
  - name: desktop
    width: 1440
    height: 900
  - name: mobile
    width: 390
    height: 844
requirements:
  - type: element-visible
    selector: "[data-testid='primary-cta']"
  - type: no-horizontal-overflow
  - type: no-console-errors
  - type: no-network-failures
  - type: no-broken-images
```

---

## The killer story

Agent says: **“Login page is complete.”**

Agent UI Loop opens real Chromium:

```
/login  desktop 1440×900   ✓
/login  mobile  390×844    ✗  no-horizontal-overflow
        scrollWidth=520  viewportWidth=390
```

Evidence: mobile screenshot + measurements — not a vibe.

Agent fixes CSS. Re-run. **Acceptance passed. VERIFIED.**

`agent-ui-loop demo` is that story, end to end, with a genuine defect.

---

## Proof

```
AGENT UI PROOF
────────────────────────────
Route                 /login       ✓
Desktop               1440×900     ✓
Mobile                390×844      ✓
Primary element visible            ✓
No horizontal overflow             ✓
No broken images                   ✓
No console errors                  ✓
Evidence:
  screenshots/desktop--login.png
  screenshots/mobile--login.png
  report.json
Commit:
  abc1234
RESULT: VERIFIED ✓
```

Proof is generated from stored run artifacts. It is never invented.

Each run writes:

```
.agent-ui-loop/runs/<run-id>/
  report.json
  report.md
  proof.txt
  screenshots/
  console.log
  network.log
  run-meta.json
```

Before/after comparison is included when a previous run exists (`agent-ui-loop compare`).

---

## Deterministic checks (layer 1)

These use the DOM, viewport geometry, console, and network — not an LLM.

| Type | What it measures |
| --- | --- |
| `no-console-errors` | `console.error` / page errors |
| `no-network-failures` | HTTP 4xx/5xx and failed requests |
| `element-exists` | `document.querySelector` |
| `element-visible` | computed style + Playwright visibility |
| `no-horizontal-overflow` | `scrollWidth` vs `innerWidth` |
| `no-broken-images` | `img.naturalWidth === 0` |
| `element-in-viewport` | `getBoundingClientRect()` vs viewport |
| `no-clipping` | `[data-testid]` elements with no intersection |

**Layer 2** (optional visual reasoning) is suggestion-only and off by default. **Layer 3** (subjective design) never auto-modifies code.

Local-first: screenshots and source are not uploaded.

---

## Agent loop

1. Agent edits the UI
2. Agent runs `agent-ui-loop run`
3. Agent reads structured failures (`--- agent-summary ---` JSON)
4. Agent fixes layer-1 failures using evidence
5. Re-run until pass
6. `agent-ui-loop prove`

Claude Code: copy or install [`.claude/skills/agent-ui-loop/SKILL.md`](.claude/skills/agent-ui-loop/SKILL.md). `init` writes the skill into the current project.

Thin adapters: [`adapters/cursor`](adapters/cursor), [`adapters/codex`](adapters/codex), [`adapters/opencode`](adapters/opencode).

---

## GitHub Action

Minimal composite action: install, run Chromium with `--with-deps`, verify, upload `.agent-ui-loop/runs/` as an artifact.

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
# After your app is actually serving a URL:
- uses: ./   # or this repository at a tag, once published
  with:
    url: http://127.0.0.1:3000
    config: agent-ui-loop.yml
```

See [`action.yml`](action.yml) and [`examples/github-workflow.yml`](examples/github-workflow.yml).

Browsers on GitHub-hosted runners need `python -m playwright install chromium --with-deps`. This Action does that. It will not start your application for you.

---

## CLI

| Command | Purpose |
| --- | --- |
| `agent-ui-loop init` | Write `agent-ui-loop.yml` + Claude skill |
| `agent-ui-loop run` | Verify (also `check`) |
| `agent-ui-loop prove` | Print proof for the latest run |
| `agent-ui-loop compare` | Before/after between last two runs |
| `agent-ui-loop demo` | Killer demo with a real mobile overflow |

`--json` for agents. Exit code `0` pass / verified, `1` failed checks, `2` config, `3` runtime (server/browser/timeout).

User-facing errors always include **what / why / how to fix**. Stack traces stay off the happy path.

---

## Development

```bash
pip install -e ".[dev]"
python -m playwright install chromium
pytest
agent-ui-loop demo
python scripts/record_gif.py   # regenerates docs/demo.gif from a live run
```

GIF recording notes: [`docs/RECORDING.md`](docs/RECORDING.md).

---

## Contributing

New checks, example configs, and thin agent adapters are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`checks/README.md`](checks/README.md).

No marketplace, cloud backend, or dashboard.

## License

MIT
