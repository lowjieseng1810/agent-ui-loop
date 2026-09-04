from __future__ import annotations

import shutil
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agent_ui_loop.config import Config, parse_config

ASSETS = Path(__file__).parent / "demo_assets"


def demo_config(url: str) -> Config:
    return parse_config(
        {
            "url": url,
            "routes": ["/login"],
            "viewports": [
                {"name": "desktop", "width": 1440, "height": 900},
                {"name": "mobile", "width": 390, "height": 844},
            ],
            "requirements": [
                {"type": "element-visible", "selector": "[data-testid='primary-cta']"},
                {"type": "no-horizontal-overflow"},
                {"type": "no-console-errors"},
                {"type": "no-network-failures"},
                {"type": "no-broken-images"},
            ],
            "timeout_ms": 15000,
        }
    )


def write_demo_app(dest: Path, *, broken: bool) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS / "index.html", dest / "index.html")
    shutil.copyfile(ASSETS / "login.html", dest / "login.html")
    shutil.copyfile(ASSETS / "mark.svg", dest / "mark.svg")
    css = ASSETS / ("styles.broken.css" if broken else "styles.fixed.css")
    shutil.copyfile(css, dest / "styles.css")
    return dest


def find_free_port(preferred: int = 48721) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/login", "/login/"}:
            self.path = "/login.html"
        super().do_GET()


def start_demo_server(root: Path, port: int) -> ThreadingHTTPServer:
    handler = partial(QuietHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
