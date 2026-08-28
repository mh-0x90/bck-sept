import os
import threading
from pathlib import Path

from .shell_server import ShellServer
from .web import make_proxy_server


def main() -> None:
    workspace = Path(os.getenv("WORKSPACE", "/workspace"))
    workspace.mkdir(parents=True, exist_ok=True)

    shell = ShellServer(("127.0.0.1", 8765), workspace)
    shell_thread = threading.Thread(target=shell.serve_forever, daemon=True)
    shell_thread.start()

    proxy = make_proxy_server(("0.0.0.0", 8080))
    try:
        print("ShellNest web listening on 0.0.0.0:8080", flush=True)
        proxy.serve_forever()
    finally:
        proxy.shutdown()
        proxy.server_close()
        shell.shutdown()
        shell.server_close()


if __name__ == "__main__":
    main()
