# Recording README visuals

Canonical command:

```bash
pip install -e ".[dev]"
python -m playwright install chromium
python scripts/build_release_assets.py
```

That runs a **real** verification (broken then fixed sample app), then writes:

- `assets/hero/agent-ui-loop-demo.gif` (also copied to `docs/demo.gif`)
- annotated failure / before-after / proof / terminal images
- diagrams and social preview
- `assets/screenshots/demo-run.txt` from `python -m agent_ui_loop demo`

`scripts/record_gif.py` is a leftover helper. Prefer `build_release_assets.py`.

Hero GIF is 1280×720 (16:9): real UI on the left, verification state on the right. Frames come from a live Playwright run, not a mock.
