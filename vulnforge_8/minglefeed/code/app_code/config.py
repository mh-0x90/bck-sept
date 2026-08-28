import os

APP_PORT = int(os.getenv("APP_PORT", "8000"))
DB_PATH = os.getenv("APP_DB", "/tmp/minglefeed.sqlite3")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
INTERNAL_PORT = int(os.getenv("INTERNAL_PORT", "9001"))
INTERNAL_FILE_LIMIT = int(os.getenv("INTERNAL_FILE_LIMIT", str(64 * 1024)))

MAX_FORM_BYTES = int(os.getenv("MAX_FORM_BYTES", str(64 * 1024)))
MAX_HTTP_WORKERS = int(os.getenv("MAX_HTTP_WORKERS", "24"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
POST_RATE_COUNT = int(os.getenv("POST_RATE_COUNT", "30"))
POST_RATE_WINDOW = int(os.getenv("POST_RATE_WINDOW", "60"))
MAX_STORED_POSTS = int(os.getenv("MAX_STORED_POSTS", "1000"))
MAX_STORED_SESSIONS = int(os.getenv("MAX_STORED_SESSIONS", "2000"))

PREVIEW_TIMEOUT = float(os.getenv("PREVIEW_TIMEOUT", "6"))
PREVIEW_LIMIT = int(os.getenv("PREVIEW_LIMIT", str(2 * 1024 * 1024)))
PREVIEW_HTML_LIMIT = int(os.getenv("PREVIEW_HTML_LIMIT", str(512 * 1024)))
PREVIEW_TEXT_LIMIT = int(os.getenv("PREVIEW_TEXT_LIMIT", "4096"))
PREVIEW_QUEUE_LIMIT = int(os.getenv("PREVIEW_QUEUE_LIMIT", "32"))
PREVIEW_WORKERS = int(os.getenv("PREVIEW_WORKERS", "2"))
PREVIEW_REDIRECT_LIMIT = int(os.getenv("PREVIEW_REDIRECT_LIMIT", "4"))
BLOCKED_PREVIEW_HOSTS = {
    item.strip().lower()
    for item in os.getenv("BLOCKED_PREVIEW_HOSTS", "localhost,::1").split(",")
    if item.strip()
}
