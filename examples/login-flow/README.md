# Login flow

Verifies the login form and primary CTA exist, then checks overflow and console on both viewports.

```bash
python examples/serve.py --fixed
agent-ui-loop run --config examples/login-flow/agent-ui-loop.yml --url http://127.0.0.1:48721
```
