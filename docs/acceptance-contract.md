# Acceptance contract (V3)

Keep this file small. Agent UI Loop orchestrates verification; it is not a CI replacement.

```yaml
task:
  name: login-page
url: http://localhost:3000
routes:
  - /login
viewports:
  - name: desktop
    width: 1440
    height: 900
  - name: mobile
    width: 390
    height: 844
# optional:
# - name: tablet
#   width: 768
#   height: 1024
requirements:
  - type: element-visible
    selector: "[data-testid='primary-cta']"
  - type: no-horizontal-overflow
  - type: no-console-errors
  - type: route-available
```

## Optional fields

```yaml
color_schemes: [light, dark]

reference:
  image: docs/reference-mobile.png
  viewport: mobile
  route: /login
  maxDiffRatio: 0.15   # omit to record evidence without failing

journeys:
  - name: sign-in
    route: /login
    viewport: desktop
    steps:
      - action: fill
        selector: "input[name=email]"
        value: ada@example.com
      - action: click
        selector: "[data-testid='primary-cta']"
      - action: visible
        selector: "[data-testid='dashboard']"

requirements:
  - type: http-status
    path: /login
    expect: 200
  - type: file-exists
    path: app/login/page.tsx
  - type: command
    command: [python, -m, pytest, -q]
  - type: a11y-names
  - type: a11y-contrast
```

Journeys support only `fill`, `click`, `visible`, `wait`. That is intentional.

`command` is an argv list (no shell) and only allowlisted binaries: pytest, python, python3, npm, npx, node, pnpm, yarn.
