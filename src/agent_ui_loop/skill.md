---
name: agent-ui-loop
description: >
  Verify that the web UI you just built actually satisfies explicit acceptance
  requirements. Open a real browser, collect evidence, fix failures, and prove
  the result. Do not say "done" without verification.
---

# Agent UI Loop

Your agent can code. Now make it prove the UI.

## When to use this skill

Use Agent UI Loop whenever you change a web UI and you are about to claim the
work is done. Typical moments:

- You implemented a page, layout, or component the user asked for
- You think a CSS/layout bug is fixed
- You need desktop and mobile evidence, not a guess
- The user asked you to verify, check, or prove the UI

Do **not** use it as a generic E2E framework, visual-regression platform, or
aesthetic redesign engine. It verifies an **acceptance contract**.

## What "verified" means

Verified means:

1. A real Chromium browser opened the configured routes at the configured viewports
2. Every requirement in `agent-ui-loop.yml` returned `passed`
3. Evidence (screenshots, measurements, logs) was written under `.agent-ui-loop/runs/<id>/`
4. `agent-ui-loop prove` prints `RESULT: VERIFIED`

If any requirement failed, the UI is **not** done. Do not tell the user it is
complete.

## Reliability layers (do not mix them up)

- **Layer 1 — deterministic (auto-actionable):** console errors, HTTP failures,
  missing/hidden elements, horizontal overflow, broken images, element outside
  the viewport. Fix these.
- **Layer 2 — visual reasoning (suggest only):** optional, not required, never
  fails the run by itself.
- **Layer 3 — subjective design (human review):** "this blue is ugly". Never
  change brand/design from this layer unless the user asked.

## Setup

From the project that contains the UI:

```bash
pip install .
python -m playwright install chromium
agent-ui-loop init --url http://localhost:3000
```

Edit `agent-ui-loop.yml`. Keep the schema small:

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

Prefer stable selectors (`data-testid`) over brittle CSS class chains.

Start the app yourself. Agent UI Loop does not start the user's server.

## Commands

```bash
agent-ui-loop run --url http://localhost:3000
agent-ui-loop check          # alias of run
agent-ui-loop prove
agent-ui-loop demo           # self-contained story with a real mobile overflow
```

`--json` prints only the agent summary.

## Workflow (mandatory after UI changes)

1. Change the frontend
2. Make sure the app is running
3. Run `agent-ui-loop run` (or `check`)
4. Read **FAILURES** and the `--- agent-summary ---` JSON
5. Open the referenced screenshot
6. Fix only layer-1 actionable failures
7. Re-run
8. Repeat until `RESULT: PASSED`
9. Run `agent-ui-loop prove`
10. Only then claim the UI is complete, citing the proof

## How to interpret failures

Each failure includes route, viewport, check, measured values, and a screenshot.

| Check | Meaning | Safe fix |
| --- | --- | --- |
| `no-horizontal-overflow` | `document` scrollWidth > viewport width | CSS: min-width, overflow-x, flex children, 100vw pitfalls |
| `element-visible` / `element-exists` | selector missing or not visible | render the element; do not hide it with `display:none` |
| `element-in-viewport` / `no-clipping` | bounding box does not intersect the viewport | layout / overflow / positioning |
| `no-console-errors` | `console.error` or page exceptions | fix the JS error; do not swallow blindly |
| `no-network-failures` | HTTP 4xx/5xx or failed requests | fix the URL or the server; ignore only if the resource is truly optional and then remove the request |
| `no-broken-images` | `img.complete && naturalWidth === 0` | fix `src` |

Trust the measurements (`scrollWidth`, `getBoundingClientRect()`, `naturalWidth`,
network status). Do not argue with them using an LLM guess.

## Using evidence

Evidence lives in `.agent-ui-loop/runs/<run-id>/`:

- `report.json` / `report.md` — full results
- `screenshots/` — real viewport captures
- `console.log` / `network.log`
- `proof.json` / `proof.txt`
- `run-meta.json` — commit, timestamps, routes

When fixing overflow, compare `scrollWidth` vs `viewportWidth` and look at the
mobile screenshot. After the fix, re-run and confirm those numbers.

## What is safe to fix

Safe without asking:

- Layout overflow, clipping, missing required elements
- Console / network / broken image failures you introduced
- Adding `data-testid` to an element the contract already names

Ask the user before:

- Changing brand colors, copy, or visual identity
- Removing features to make a check pass
- Weakening or deleting requirements

Never:

- Fake a pass
- Delete screenshots instead of fixing the UI
- Skip mobile because desktop passed

## When to re-run

Re-run after every layout/CSS/DOM change intended to address a failure.
Do not batch ten speculative CSS tweaks without evidence between them if the
first re-run still fails.

## When to stop

Stop when:

- `agent-ui-loop prove` says `RESULT: VERIFIED`
- or a failure is outside the contract (backend down, auth wall) and you
  have reported that blocker with evidence

Do not keep restyling after verification unless the user asked for design work.

## First-run without a project

```bash
agent-ui-loop demo
```

This serves a login page with a **real** mobile CTA overflow, detects it with
Playwright, applies the CSS fix, re-verifies, and prints proof.
