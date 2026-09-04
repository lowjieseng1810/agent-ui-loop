# Check template

```python
from agent_ui_loop.checks.base import result

class ExampleCheck:
    type = "example-check"
    description = "What it measures."
    domain = "ui"
    scope = "page"
    why = "Why an agent should treat a failure as incomplete work."

    def run(self, requirement, ctx):
        measured = {"example": True}
        return result(requirement, ctx, "passed", measured, "ok", why=self.why)
```

Inputs come from `requirement.selector` and `requirement.extra`.
Evidence must include the actual measurement, not a paraphrase.
