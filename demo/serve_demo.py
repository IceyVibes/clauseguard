"""Serve the ClauseGuard fictional demo websites.

Usage:
    python demo/serve_demo.py

Configuration via environment variables:
    DEMO_HOST  (default: 127.0.0.1)
    DEMO_PORT  (default: 5500)

When run inside a container, set DEMO_HOST=0.0.0.0 so the port mapping
to the host works correctly.
"""
from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent


def main() -> None:
    host = os.environ.get("DEMO_HOST", "127.0.0.1")
    port = int(os.environ.get("DEMO_PORT", "5500"))

    handler = partial(SimpleHTTPRequestHandler, directory=str(DEMO_DIR))
    server = ThreadingHTTPServer((host, port), handler)

    print("=== ClauseGuard demo server ===")
    print(f"Serving directory: {DEMO_DIR}")
    print(f"Listening on     : http://{host}:{port}")
    print(f"Scenario gallery : http://{host}:{port}/index.html")
    print("Press CTRL+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down demo server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
