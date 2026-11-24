"""Standalone healthcheck used by compose.yaml.

Using a real script file (instead of an inline `python -c "..."` one-liner)
avoids quoting/escaping differences between Docker's and Podman's healthcheck
command handling, which can otherwise mangle an inline command.
"""
import sys
import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
