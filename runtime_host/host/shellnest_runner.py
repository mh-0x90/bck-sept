#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, "/opt/apps/shellnest")
from app_code.shell_server import ShellServer
from app_code.web import make_proxy_server


def main() -> None:
    web_port = int(os.environ.get("SHELLNEST_WEB_PORT", "8108"))
    shell_port = int(os.environ.get("SHELLNEST_INTERNAL_PORT", "8765"))
    workspace = Path(os.environ.get("WORKSPACE", "/workspace"))
    workspace.mkdir(parents=True, exist_ok=True)

    shell = ShellServer(("127.0.0.1", shell_port), workspace)
    thread = threading.Thread(target=shell.serve_forever, daemon=True)
    thread.start()

    proxy = make_proxy_server(("0.0.0.0", web_port), shell_port=shell_port)
    try:
        print(f"ShellNest web listening on 0.0.0.0:{web_port}", flush=True)
        proxy.serve_forever()
    finally:
        proxy.shutdown()
        proxy.server_close()
        shell.shutdown()
        shell.server_close()


if __name__ == "__main__":
    main()
