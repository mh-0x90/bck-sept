#!/usr/bin/env python3
from __future__ import annotations

import os
import pwd
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

PROCESSES: list[tuple[str, subprocess.Popen]] = []
STOPPING = False
RUNTIME = Path("/tmp/runtime")
PARCELPAD_SECRETS = Path("/run/parcelpad")


def drop_to(user: str):
    record = pwd.getpwnam(user)

    def apply() -> None:
        os.setgroups([])
        os.setgid(record.pw_gid)
        os.setuid(record.pw_uid)

    return apply


def base_env(home: str) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
        "HOME": home,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    if "TZ" in os.environ:
        env["TZ"] = os.environ["TZ"]
    return env


def start(name: str, argv: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None, user: str | None = None) -> subprocess.Popen:
    merged = base_env(str(RUNTIME / name))
    if env:
        merged.update(env)
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=merged,
        stdin=subprocess.DEVNULL,
        preexec_fn=drop_to(user) if user else None,
    )
    PROCESSES.append((name, proc))
    return proc


def wait_port(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError(f"port {port} did not become ready")


def wait_http(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=0.6) as response:
                if 200 <= response.status < 500:
                    return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError(f"service did not become ready: {url}")


def pg_cluster() -> tuple[str, str]:
    output = subprocess.check_output(["pg_lsclusters", "--no-header"], text=True).strip().splitlines()
    if not output:
        raise RuntimeError("PostgreSQL cluster is unavailable")
    parts = output[0].split()
    return parts[0], parts[1]


def postgres_sql(sql: str) -> None:
    subprocess.run(
        ["runuser", "-u", "postgres", "--", "psql", "-v", "ON_ERROR_STOP=1", "-d", "postgres", "-f", "-"],
        input=sql,
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def write_secret(name: str, value: str) -> Path:
    PARCELPAD_SECRETS.mkdir(parents=True, exist_ok=True)
    path = PARCELPAD_SECRETS / name
    path.write_text(value + "\n", encoding="utf-8")
    os.chmod(path, 0o444)
    return path


def prepare_parcelpad_secrets() -> tuple[str, str]:
    os.umask(0o077)
    db_password = secrets.token_urlsafe(36)
    app_secret = secrets.token_urlsafe(48)
    receiver_token = secrets.token_urlsafe(36)
    username = (os.environ.get("PARCELPAD_USERNAME") or os.environ.get("LOGIN_USERNAME") or "operator").strip() or "operator"
    password = (os.environ.get("PARCELPAD_PASSWORD") or os.environ.get("LOGIN_PASSWORD") or "").strip()
    if not password:
        password = secrets.token_urlsafe(24)

    write_secret("db_password", db_password)
    write_secret("app_secret", app_secret)
    write_secret("login_password", password)
    write_secret("receiver_token", receiver_token)
    os.chmod(PARCELPAD_SECRETS, 0o755)
    print(f"ParcelPad local login: {username} / {password}", flush=True)
    return db_password, username


def prepare_postgres(password: str) -> None:
    version, cluster = pg_cluster()
    subprocess.run(
        ["pg_ctlcluster", "--skip-systemctl-redirect", version, cluster, "start"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    safe = password.replace("'", "''")
    postgres_sql(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='parcelpad') THEN "
        "CREATE ROLE parcelpad LOGIN; END IF; END $$;\n"
        f"ALTER ROLE parcelpad PASSWORD '{safe}';\n"
    )
    exists = subprocess.check_output(
        ["runuser", "-u", "postgres", "--", "psql", "-tAc", "SELECT 1 FROM pg_database WHERE datname='parcelpad'"],
        text=True,
    ).strip()
    if exists != "1":
        subprocess.run(["runuser", "-u", "postgres", "--", "createdb", "-O", "parcelpad", "parcelpad"], check=True)

    init_env = os.environ.copy()
    init_env["PGPASSWORD"] = password
    subprocess.run(
        ["psql", "-h", "127.0.0.1", "-U", "parcelpad", "-d", "parcelpad", "-v", "ON_ERROR_STOP=1", "-f", "/opt/apps/parcelpad/app_code/db/init.sql"],
        env=init_env,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def terminate(_signum=None, _frame=None) -> None:
    global STOPPING
    if STOPPING:
        return
    STOPPING = True
    for _name, proc in reversed(PROCESSES):
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 8
    for _name, proc in reversed(PROCESSES):
        if proc.poll() is None:
            try:
                proc.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                proc.kill()
    try:
        version, cluster = pg_cluster()
        subprocess.run(
            ["pg_ctlcluster", "--skip-systemctl-redirect", version, cluster, "stop"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main() -> int:
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)

    for name in ("dashboard", "companyemail", "mailbox", "minglefeed", "parcel-room", "parcelpad", "pulseboard", "quickcart", "shellnest", "documentsmng"):
        (RUNTIME / name).mkdir(parents=True, exist_ok=True)

    db_password, parcelpad_username = prepare_parcelpad_secrets()
    prepare_postgres(db_password)

    start(
        "companyemail-mailpit",
        [
            "/usr/local/bin/mailpit",
            "--listen", "0.0.0.0:8025",
            "--smtp", "127.0.0.1:1025",
            "--database", "/tmp/runtime/companyemail/mailpit.db",
            "--disable-version-check",
        ],
        user="companyemail",
    )
    wait_port(1025)

    companyemail_env = {
        "PORT": "8101",
        "DATABASE_PATH": "/tmp/runtime/companyemail/companyemail.db",
        "SMTP_HOST": "127.0.0.1",
        "SMTP_PORT": "1025",
    }
    if os.environ.get("COMPANYEMAIL_APP_SECRET"):
        companyemail_env["APP_SECRET"] = os.environ["COMPANYEMAIL_APP_SECRET"]
    start(
        "companyemail",
        ["/opt/venvs/companyemail/bin/python", "app.py"],
        cwd="/opt/apps/companyemail/app_code",
        user="companyemail",
        env=companyemail_env,
    )

    start(
        "mailbox",
        ["/usr/sbin/nginx", "-c", "/opt/host/nginx-mailbox.conf", "-g", "daemon off;"],
    )

    start(
        "minglefeed",
        ["/opt/venvs/minglefeed/bin/python", "app.py"],
        cwd="/opt/apps/minglefeed/app_code",
        user="minglefeed",
        env={
            "APP_DB": "/tmp/runtime/minglefeed/minglefeed.sqlite3",
            "APP_PORT": "8103",
        },
    )

    parcel_key = os.environ.get(
        "PARCEL_TMP_ENCRYPTION_KEY",
        "VEVTVF9QQVJDRUxfUk9PTV9LRVlfMzJfQllURVMhISE=",
    )
    start(
        "parcel-room",
        [
            "/opt/venvs/parcel-room/bin/python", "-m", "uvicorn",
            "app_code.app:app", "--host", "0.0.0.0", "--port", "8104",
        ],
        cwd="/opt/apps/parcel-room",
        user="parcelroom",
        env={
            "PARCEL_TMP_ENCRYPTION_KEY": parcel_key,
            "PARCEL_DB_PATH": "/tmp/runtime/parcel-room/parcel_room.db",
        },
    )

    receiver_delay = os.environ.get("PARCELPAD_RECEIVER_DELAY", os.environ.get("RECEIVER_DELAY", "6"))
    receiver_env = {
        "RECEIVER_DELAY": receiver_delay,
        "RECEIVER_TOKEN_FILE": "/run/parcelpad/receiver_token",
    }
    start(
        "parcelpad-receiver",
        ["/opt/venvs/parcelpad/bin/python", "-m", "app_code.receiver"],
        cwd="/opt/apps/parcelpad",
        user="parcelpad",
        env=receiver_env,
    )
    wait_http("http://127.0.0.1:9000/health")

    parcelpad_env = {
        "DATABASE_HOST": "127.0.0.1",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "parcelpad",
        "DATABASE_USER": "parcelpad",
        "DATABASE_PASSWORD_FILE": "/run/parcelpad/db_password",
        "APP_SECRET_FILE": "/run/parcelpad/app_secret",
        "LOGIN_USERNAME": parcelpad_username,
        "LOGIN_PASSWORD_FILE": "/run/parcelpad/login_password",
        "RECEIVER_TOKEN_FILE": "/run/parcelpad/receiver_token",
        "INTERNAL_URL": "http://127.0.0.1:9000/internal",
        "INTERNAL_NOTE": os.environ.get("PARCELPAD_INTERNAL_NOTE", "local-test-note"),
        "COOKIE_SECURE": os.environ.get("PARCELPAD_COOKIE_SECURE", "0"),
    }
    start(
        "parcelpad",
        [
            "/opt/venvs/parcelpad/bin/gunicorn",
            "--workers", "2", "--threads", "4",
            "--bind", "0.0.0.0:8105", "--access-logfile", "-",
            "app_code:create_app()",
        ],
        cwd="/opt/apps/parcelpad",
        user="parcelpad",
        env=parcelpad_env,
    )

    start(
        "pulseboard",
        [
            "/opt/venvs/pulseboard/bin/python", "-m", "uvicorn",
            "app_code.server.main:app", "--host", "0.0.0.0", "--port", "8106",
        ],
        cwd="/opt/apps/pulseboard",
        user="pulseboard",
    )

    start(
        "quickcart",
        [
            "/opt/venvs/quickcart/bin/gunicorn",
            "--bind", "0.0.0.0:8107", "--workers", "2", "--threads", "2",
            "app:app",
        ],
        cwd="/opt/apps/quickcart/app_code",
        user="quickcart",
        env={
            "AMK": os.environ.get("QUICKCART_AMK", "test_id"),
            "APP_SECRET": os.environ.get("QUICKCART_APP_SECRET", "app_secret"),
            "LOG_HMAC_KEY": os.environ.get(
                "QUICKCART_LOG_HMAC_KEY",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ),
            "LOG_SERVICE_URL": "http://127.0.0.1:8107",
            "LOG_ROUTE_ALLOWED_IPS": "127.0.0.1,::1",
            "QUICKCART_LOG_DIR": "/tmp/runtime/quickcart/logs",
        },
    )

    start(
        "shellnest",
        ["/opt/venvs/shellnest/bin/python", "/opt/host/shellnest_runner.py"],
        user="shellnest",
        env={
            "PYTHONPATH": "/opt/apps/shellnest",
            "APP_ENV": os.environ.get("SHELLNEST_APP_ENV", "testing"),
            "WORKSPACE": "/tmp/runtime/shellnest/workspace",
            "SHELLNEST_WEB_PORT": "8108",
            "SHELLNEST_INTERNAL_PORT": "8765",
        },
    )

    start(
        "documentsmng",
        [
            "/opt/venvs/documentsmng/bin/gunicorn",
            "--bind", "0.0.0.0:8109", "--workers", "2", "--threads", "2",
            "app:create_app()",
        ],
        cwd="/opt/apps/documentsmng",
        user="documentsmng",
    )

    start(
        "dashboard",
        [sys.executable, "/opt/host/dashboard.py"],
        user="dashboard",
        env={"HUB_PORT": "8080"},
    )

    while not STOPPING:
        for name, proc in PROCESSES:
            code = proc.poll()
            if code is not None:
                print(f"process exited: {name} ({code})", file=sys.stderr, flush=True)
                terminate()
                return code or 1
        time.sleep(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
