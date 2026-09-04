# Recording the README GIF

The GIF in `docs/demo.gif` is built from **real** Playwright screenshots of the
demo login page (broken mobile overflow, then the CSS fix).

## Generate

```bash
pip install -e ".[dev]"
python -m playwright install chromium
python scripts/record_gif.py
```

This:

1. Serves the demo app with the intentional `min-width: 520px` CTA row
2. Runs Agent UI Loop (desktop + mobile)
3. Applies the fix
4. Re-runs
5. Composites captions + screenshots into `docs/demo.gif`

Sequence (about 16s):

| Time | Frame |
| --- | --- |
| 0–2s | Agent claims the login page is complete |
| 2–4s | Desktop capture |
| 4–6s | Mobile failure |
| 6–8s | Evidence: scrollWidth vs viewportWidth |
| 8–11s | CSS fix |
| 11–14s | Re-check |
| 14–16s | VERIFIED |

Nothing in the GIF is a mock UI or a fabricated measurement.
