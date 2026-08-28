import os
from http.server import ThreadingHTTPServer

from db import init_db
from routes import Handler

PORT = int(os.environ.get("PORT", "3000"))


def serve(port=PORT):
    init_db()
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
