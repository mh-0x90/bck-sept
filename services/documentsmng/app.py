import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request
from db import get_connection, init_db
from worker import Storage, process_pending_jobs, process_pending_distribution_tasks

storage = Storage()
SECRET_KEY = (os.environ.get("APP_SECRET") or secrets.token_hex(32)).encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
        )
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def sign_token(user_id: int) -> str:
    val = str(user_id)
    sig = hmac.new(SECRET_KEY, val.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{val}.{sig}"


def verify_token(token: str) -> int | None:
    if not token or "." not in token:
        return None
    val, sig = token.split(".", 1)
    if not val.isdigit():
        return None
    expected = hmac.new(SECRET_KEY, val.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return int(val)


def get_current_user(conn) -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "session" in request.cookies:
        token = request.cookies.get("session", "")

    user_id = verify_token(token)
    if not user_id:
        return None
    user = conn.execute("SELECT id, username, tenant_id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(user) if user else None


def create_app(test_config=None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    db_path = app.config.get("DB_PATH")
    if db_path:
        init_db(db_path)
    else:
        init_db()

    def db():
        if db_path:
            return get_connection(db_path)
        return get_connection()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/export")
    @app.get("/tenant-export")
    def export_page():
        return render_template("export.html")

    @app.get("/distribution")
    @app.get("/distribution-tasks")
    def distribution_page():
        return render_template("distribution.html")

    @app.post("/api/auth/login")
    def login():
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400

        with db() as conn:
            user = conn.execute("SELECT id, password_hash, tenant_id, role FROM users WHERE username = ?", (username,)).fetchone()
            if not user or not verify_password(password, user["password_hash"]):
                return jsonify({"error": "invalid credentials"}), 401

            token = sign_token(user["id"])
            return jsonify({"token": token, "user_id": user["id"], "tenant_id": user["tenant_id"], "role": user["role"]}), 200

    @app.post("/api/tenants")
    def create_tenant():
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        with db() as conn:
            cur = conn.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
            return jsonify({"id": cur.lastrowid, "name": name}), 201

    @app.post("/api/users")
    def create_user():
        data = request.get_json() or {}
        username = data.get("username")
        password = data.get("password", "DefaultPass123!")
        tenant_id = data.get("tenant_id")
        role = data.get("role", "user")
        if not username or not tenant_id:
            return jsonify({"error": "username and tenant_id are required"}), 400
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, tenant_id, role) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), tenant_id, role),
            )
            return jsonify({"id": cur.lastrowid, "username": username, "tenant_id": tenant_id, "role": role}), 201

    @app.post("/api/documents")
    def create_document():
        with db() as conn:
            user = get_current_user(conn)
            if not user:
                return jsonify({"error": "unauthorized"}), 401

            data = request.get_json() or {}
            tenant_id = user["tenant_id"]
            title = data.get("title")
            content = data.get("content", "")
            if not title:
                return jsonify({"error": "title is required"}), 400

            cur = conn.execute(
                "INSERT INTO documents (tenant_id, title, content) VALUES (?, ?, ?)",
                (tenant_id, title, content),
            )
            return jsonify({"id": cur.lastrowid, "tenant_id": tenant_id, "title": title}), 201

    @app.post("/api/documents/<int:doc_id>/transfer")
    def transfer_document(doc_id: int):
        with db() as conn:
            user = get_current_user(conn)
            if not user:
                return jsonify({"error": "unauthorized"}), 401
            if user["role"] != "admin":
                return jsonify({"error": "forbidden"}), 403

            data = request.get_json() or {}
            new_tenant_id = data.get("new_tenant_id")
            if not new_tenant_id:
                return jsonify({"error": "new_tenant_id required"}), 400

            doc = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not doc:
                return jsonify({"error": "document not found"}), 404

            conn.execute("UPDATE documents SET tenant_id = ? WHERE id = ?", (new_tenant_id, doc_id))
            return jsonify({"status": "transferred", "document_id": doc_id, "tenant_id": new_tenant_id}), 200

    @app.post("/api/exports")
    def request_export():
        with db() as conn:
            user = get_current_user(conn)
            if not user:
                return jsonify({"error": "unauthorized"}), 401

            data = request.get_json() or {}
            document_id = data.get("document_id")
            destination = data.get("destination")
            execute_at = data.get("execute_at")
            if not execute_at:
                execute_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            if not document_id or not destination:
                return jsonify({"error": "document_id and destination are required"}), 400

            doc = conn.execute("SELECT id, tenant_id FROM documents WHERE id = ?", (document_id,)).fetchone()
            if not doc:
                return jsonify({"error": "document not found"}), 404

            if doc["tenant_id"] != user["tenant_id"]:
                return jsonify({"error": "forbidden"}), 403

            cur = conn.execute(
                "INSERT INTO export_jobs (document_id, requester_id, destination, status, execute_at) VALUES (?, ?, ?, 'pending', ?)",
                (document_id, user["id"], destination, execute_at),
            )
            return jsonify({"job_id": cur.lastrowid, "status": "pending", "execute_at": execute_at}), 202

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "documentsmng"}), 200

    @app.get("/api/exports/<int:job_id>")
    def get_export_status(job_id: int):
        with db() as conn:
            user = get_current_user(conn)
            if not user:
                return jsonify({"error": "unauthorized"}), 401
            job = conn.execute(
                "SELECT id, document_id, requester_id, destination, status, execute_at, created_at FROM export_jobs WHERE id = ? AND requester_id = ?",
                (job_id, user["id"]),
            ).fetchone()
            if not job:
                return jsonify({"error": "not found"}), 404
            return jsonify(dict(job)), 200

    @app.post("/api/worker/run")
    def run_worker():
        data = request.get_json(silent=True) or {}
        current_time = data.get("current_time")
        with db() as conn:
            processed = process_pending_jobs(conn, storage, current_time=current_time)
            return jsonify({"status": "completed", "processed": processed}), 200

    @app.post("/api/distribution")
    def request_distribution():
        with db() as conn:
            user = get_current_user(conn)
            if not user:
                return jsonify({"error": "unauthorized"}), 401

            data = request.get_json() or {}
            document_id = data.get("document_id")
            target_endpoint = data.get("target_endpoint")
            scheduled_at = data.get("scheduled_at")
            is_legacy = bool(data.get("legacy") or data.get("omit_tenant"))
            tenant_id = None if is_legacy else data.get("tenant_id", user["tenant_id"])

            if not scheduled_at:
                scheduled_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            if not document_id or not target_endpoint:
                return jsonify({"error": "document_id and target_endpoint are required"}), 400

            doc = conn.execute("SELECT id, tenant_id FROM documents WHERE id = ?", (document_id,)).fetchone()
            if not doc:
                return jsonify({"error": "document not found"}), 404

            if not is_legacy and doc["tenant_id"] != user["tenant_id"] and user["role"] != "admin":
                return jsonify({"error": "forbidden"}), 403

            cur = conn.execute(
                "INSERT INTO distribution_tasks (document_id, requester_id, tenant_id, target_endpoint, status, scheduled_at) VALUES (?, ?, ?, ?, 'pending', ?)",
                (document_id, user["id"], tenant_id, target_endpoint, scheduled_at),
            )
            return jsonify({"task_id": cur.lastrowid, "status": "pending", "scheduled_at": scheduled_at, "tenant_id": tenant_id}), 202

    @app.get("/api/distribution/<int:task_id>")
    def get_distribution_status(task_id: int):
        with db() as conn:
            user = get_current_user(conn)
            if not user:
                return jsonify({"error": "unauthorized"}), 401
            task = conn.execute(
                "SELECT id, document_id, requester_id, tenant_id, target_endpoint, status, scheduled_at, created_at FROM distribution_tasks WHERE id = ? AND requester_id = ?",
                (task_id, user["id"]),
            ).fetchone()
            if not task:
                return jsonify({"error": "not found"}), 404
            return jsonify(dict(task)), 200

    @app.post("/api/distribution/worker/run")
    def run_distribution_worker():
        data = request.get_json(silent=True) or {}
        current_time = data.get("current_time")
        with db() as conn:
            processed = process_pending_distribution_tasks(conn, storage, current_time=current_time)
            return jsonify({"status": "completed", "processed": processed}), 200

    return app
