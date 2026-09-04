# Proof format (schemaVersion 3)

Proof means **auditable verification evidence**, not a cryptographic proof.

Each run writes:

```
.agent-ui-loop/runs/<run-id>/
  proof.json
  proof.md
  proof.txt
  github.md
  report.json
  report.md
  graph.json
  run-meta.json
  screenshots/
  logs/console.log
  logs/network.log
```

`proof.json` kind is `agent-completion-proof`.

It answers:

- What task was claimed complete?
- Which requirements were checked?
- How many passed / failed (unique requirement types)?
- Which git commit (when available)?
- Where are screenshots and logs?

`github.md` is the PR/Actions-friendly summary.

See `graph.json` for TASK → REQUIREMENT → CHECK → OBSERVATION → EVIDENCE → VERDICT.
