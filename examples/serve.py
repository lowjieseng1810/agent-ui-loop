"""Serve the bundled demo fixture so example contracts can run against a real page."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from agent_ui_loop.demo import find_free_port, start_demo_server, write_demo_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Agent UI Loop demo fixture.")
    parser.add_argument("--broken", action="store_true", help="serve the overflowing CTA (default)")
    parser.add_argument("--fixed", action="store_true", help="serve the CSS-fixed page")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    dest = Path(".agent-ui-loop") / "examples-fixture"
    app = write_demo_app(dest, broken=not args.fixed)
    port = args.port or find_free_port(48721)
    server = start_demo_server(app, port)
    url = f"http://127.0.0.1:{port}"
    print(f"Serving {app} at {url}/login")
    print("In another terminal:")
    print(f"  agent-ui-loop run --config examples/mobile-overflow/agent-ui-loop.yml --url {url}")
    print("Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
