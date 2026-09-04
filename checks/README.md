# Adding a check (few minutes)

1. Copy `checks/TEMPLATE.md`.
2. Add `src/agent_ui_loop/checks/your_check.py` with:

```python
class YourCheck:
    type = "your-check"
    description = "One sentence."
    domain = "ui"       # ui | runtime | http | test | code
    scope = "page"      # page (browser) | run (once)
    why = "Why this belongs in an acceptance contract."

    def run(self, requirement, ctx):
        ...
        return result(requirement, ctx, "passed"|"failed", evidence, message, why=self.why)
```

3. Register it in `src/agent_ui_loop/checks/__init__.py` `REGISTRY`.
4. Add the type to `KNOWN_REQUIREMENT_TYPES` in `config.py`.
5. Add a fixture HTML page + a test in `tests/`.
6. Mention it in `docs/acceptance-contract.md`.

Keep checks deterministic. Do not call an LLM. Do not upload data.
