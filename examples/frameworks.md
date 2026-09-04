# Framework notes

Agent UI Loop is framework-agnostic. Point `url` at whatever serves HTML.

- **Plain HTML** — `python -m http.server` or the built-in demo.
- **Vite / React** — `url: http://localhost:5173` (or your port).
- **Next.js** — `url: http://localhost:3000` plus `routes` for app router paths.

Prefer `data-testid` in the acceptance contract. Do not put framework adapters in core.
