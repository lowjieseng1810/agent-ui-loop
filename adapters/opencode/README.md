# OpenCode adapter (thin)

Invoke the same CLI any other agent uses:

```
agent-ui-loop run --json
```

JSON shape (abridged):

```json
{
  "status": "failed",
  "failures": [
    {
      "check": "no-horizontal-overflow",
      "route": "/login",
      "viewport": {"name": "mobile", "width": 390, "height": 844},
      "evidence": {"scrollWidth": 520, "viewportWidth": 390},
      "actionable": true,
      "layer": 1
    }
  ]
}
```

Fix actionable layer-1 items, re-run, then `agent-ui-loop prove`.
