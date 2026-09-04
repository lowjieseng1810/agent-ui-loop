from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from agent_ui_loop.demo import find_free_port

FIXTURES = Path(__file__).parent / "fixtures"


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture
def serve_dir():
    servers: list[ThreadingHTTPServer] = []

    def _serve(directory: Path) -> str:
        port = find_free_port()
        handler = partial(Handler, directory=str(directory))
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
        return f"http://127.0.0.1:{port}"

    yield _serve
    for server in servers:
        server.shutdown()
        server.server_close()
