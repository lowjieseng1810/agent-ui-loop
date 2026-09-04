# Visual assets

Every product screenshot and the hero GIF is generated from a **real** Agent UI Loop run (`scripts/build_release_assets.py`). Diagrams and the social preview are brand graphics (not fake browser chrome).

| File | Purpose | Source | README |
| --- | --- | --- | --- |
| `hero/agent-ui-loop-demo.gif` | 16:9 workflow (UI left, verification right) | Real Chromium. Fail frames: 390px viewport chrome + overflowing CTA continuing outside the frame. | Hero |
| `hero/agent-ui-loop-hero.png` | Static FAIL frame from the same composition | Real mobile screenshot + real measurements | From “Done” to “Proved” |
| `screenshots/mobile-failure.png` | Annotated mobile fail | Real mobile screenshot + actual `scrollWidth` / `viewportWidth` | From "Done" to "Proved" |
| `screenshots/before-after.png` | Same page before/after | Real mobile screenshots | From "Done" to "Proved" |
| `screenshots/proof.png` | Proof presentation | Real `proof.txt` from a verified run | Proof |
| `screenshots/terminal-verified.png` | Terminal | Actual `agent-ui-loop demo` stdout | Quickstart |
| `screenshots/demo-run.txt` | Raw CLI transcript | Same demo process | Linked from terminal caption |
| `diagrams/verification-loop.svg` | WRITE→…→PROVE | Drawn SVG | How it works |
| `diagrams/acceptance-flow.svg` | Contract → browser → evidence → proof | Drawn SVG | Acceptance |
| `social/github-social-preview.png` | 1280×640 share image | Brand graphic | Not auto-applied as GitHub social preview |
| `examples/proof.json` | Raw proof | Copy of a verified `proof.json` | Proof |

Regenerate:

```bash
pip install -e ".[dev]"
python -m playwright install chromium
python scripts/build_release_assets.py
```

Do not invent GitHub Actions UI screenshots. The Action example in the README is the real `action.yml` usage (`uses: ./`).
