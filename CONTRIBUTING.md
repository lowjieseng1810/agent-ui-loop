# Contributing

Thanks for helping agents prove that a UI actually works.

## What this project is

Acceptance-driven UI verification with evidence:

REQUIRE → RUN → VERIFY → EVIDENCE → FIX → PROVE

It is not a SaaS, dashboard, visual-regression cloud, or aesthetic redesign tool.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
pytest
agent-ui-loop demo
```

## Good contributions

- New **deterministic** checks with tests and a fixture page
- Example configs under `examples/`
- Thin agent adapters under `adapters/` (docs + snippets, not forks of the runner)
- Reliability and error-message improvements

## Not a fit

- Marketplaces / plugin stores
- Cloud backends that upload screenshots by default
- Subjective design auto-editors
- Giant DSLs

## Check contract

1. Measure something real in the browser
2. Record the numbers in `evidence`
3. Fail closed on missing required elements
4. Keep the YAML schema small

## Tests

Do not add tests that stub away Playwright for checks that claim to observe a page. Fixture HTML + a local HTTP server + Chromium is the expected pattern (see `tests/`).
