# Examples

Each folder is a real acceptance contract for the bundled login fixture.

```bash
pip install .
python -m playwright install chromium

# Terminal 1 — real page
python examples/serve.py

# Terminal 2 — pick a contract (replace the URL with the one serve.py printed)
agent-ui-loop run --config examples/mobile-overflow/agent-ui-loop.yml --url http://127.0.0.1:48721
```

| Example | What it proves |
| --- | --- |
| [mobile-overflow](mobile-overflow/) | Desktop can pass while mobile overflow fails |
| [responsive-ui](responsive-ui/) | Same checks on two viewports |
| [login-flow](login-flow/) | Form fields present + overflow + console |
| [journey](journey/) | Click Continue → dashboard visible |

`examples/serve.py --broken` (default) is the failing mobile case. `--fixed` serves the passing CSS.

Canonical one-command story remains `agent-ui-loop demo`, which runs fail → fix sample CSS → reverify itself.
