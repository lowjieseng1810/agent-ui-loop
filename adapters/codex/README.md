# Codex adapter (thin)

Core verification stays in `agent-ui-loop`. Codex should shell out to the CLI.

```
pip install agent-ui-loop
python -m playwright install chromium
agent-ui-loop init
agent-ui-loop run
agent-ui-loop prove
```

Read `--- agent-summary ---` from stdout. Evidence is local under `.agent-ui-loop/` and is never uploaded.
