# Mobile overflow

Desktop 1440×900 can look fine while 390×844 overflows. This contract fails on the bundled fixture until CSS constrains the CTA.

```bash
python examples/serve.py --broken
agent-ui-loop run --config examples/mobile-overflow/agent-ui-loop.yml --url http://127.0.0.1:48721
```

Expected on `--broken`: `no-horizontal-overflow` fails on mobile with `scrollWidth` > `viewportWidth`.
Expected on `--fixed`: all checks pass.
