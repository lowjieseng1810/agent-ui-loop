# Network and privacy

Agent UI Loop is **local-first**.

Default behavior:

- Opens the URL you configured in local Chromium.
- Writes screenshots, logs, and proof under `.agent-ui-loop/` on disk.
- Does **not** upload screenshots, source, or reports anywhere.

GitHub Action: artifacts are uploaded to **your** GitHub Actions artifact store when you use the Action. That is explicit GitHub infrastructure, not a silent third-party leak.

External vision/LLM providers: **off**. There is no default API call. Do not set a provider unless you intend traffic to leave the machine.

`command` checks run subprocesses you listed in YAML as argv (no shell). Only allowlisted binaries. Do not point this at untrusted config from the internet.
