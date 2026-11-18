import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH, MAX_STORED_POSTS, MAX_STORED_SESSIONS


def connect():
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                sid TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                body TEXT NOT NULL,
                media_url TEXT,
                preview_url TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS previews (
                post_id INTEGER PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                kind TEXT,
                title TEXT,
                description TEXT,
                image_url TEXT,
                content_type TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )


def hash_password(password):
    salt = os.urandom(16)
    rounds = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        _, rounds, salt_hex, digest_hex = stored.split("$", 3)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_user(username, password):
    with connect() as db:
        cur = db.execute(
            "INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), utc_now()),
        )
        return cur.lastrowid


def get_user_by_name(username):
    with connect() as db:
        return db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user(user_id):
    with connect() as db:
        return db.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def create_session(user_id):
    sid = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute(
            "INSERT INTO sessions(sid, user_id, created_at) VALUES (?, ?, ?)",
            (sid, user_id, utc_now()),
        )
        db.execute(
            """
            DELETE FROM sessions
            WHERE sid NOT IN (
                SELECT sid FROM sessions ORDER BY created_at DESC LIMIT ?
            )
            """,
            (MAX_STORED_SESSIONS,),
        )
    return sid


def delete_session(sid):
    if not sid:
        return
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE sid = ?", (sid,))


def user_for_session(sid):
    if not sid:
        return None
    with connect() as db:
        return db.execute(
            """
            SELECT users.id, users.username, users.created_at
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.sid = ?
            """,
            (sid,),
        ).fetchone()


def create_post(user_id, body, media_url, preview_url):
    with connect() as db:
        cur = db.execute(
            """
            INSERT INTO posts(user_id, body, media_url, preview_url, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, body, media_url or None, preview_url or None, utc_now()),
        )
        post_id = cur.lastrowid
        if preview_url:
            db.execute(
                "INSERT INTO previews(post_id, status, updated_at) VALUES (?, 'queued', ?)",
                (post_id, utc_now()),
            )
        db.execute(
            """
            DELETE FROM posts
            WHERE id NOT IN (
                SELECT id FROM posts ORDER BY id DESC LIMIT ?
            )
            """,
            (MAX_STORED_POSTS,),
        )
        return post_id


def list_posts():
    with connect() as db:
        return db.execute(
            """
            SELECT p.*, u.username,
                   v.status AS preview_status, v.kind AS preview_kind,
                   v.title AS preview_title, v.description AS preview_description,
                   v.image_url AS preview_image_url, v.content_type AS preview_content_type
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN previews v ON v.post_id = p.id
            ORDER BY p.id DESC
            LIMIT 100
            """
        ).fetchall()


def pending_preview_ids():
    with connect() as db:
        rows = db.execute(
            "SELECT post_id FROM previews WHERE status IN ('queued', 'processing') ORDER BY post_id"
        ).fetchall()
        return [row["post_id"] for row in rows]


def get_preview_target(post_id):
    with connect() as db:
        return db.execute(
            "SELECT preview_url FROM posts WHERE id = ?", (post_id,)
        ).fetchone()


def set_preview(post_id, **fields):
    allowed = {"status", "kind", "title", "description", "image_url", "content_type"}
    items = [(key, value) for key, value in fields.items() if key in allowed]
    if not items:
        return
    setters = ", ".join(f"{key} = ?" for key, _ in items) + ", updated_at = ?"
    values = [value for _, value in items] + [utc_now(), post_id]
    with connect() as db:
        db.execute(f"UPDATE previews SET {setters} WHERE post_id = ?", values)


def preview_states():
    with connect() as db:
        rows = db.execute(
            "SELECT post_id, status, kind, title, description, image_url, content_type FROM previews"
        ).fetchall()
        return {str(row["post_id"]): dict(row) for row in rows}
