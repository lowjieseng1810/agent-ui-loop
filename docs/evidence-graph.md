# Evidence graph

`graph.json` (also embedded in `report.json` as `graph`) is a small node/edge list:

```
TASK → REQUIREMENT → CHECK → OBSERVATION → EVIDENCE → VERDICT
```

Each observation records route, viewport, environment (URL, color scheme, commit).

Each evidence node stores measured values, screenshot path, optional command, timestamp.

This is for agents and humans to trace a failure. It is not a knowledge graph product.
