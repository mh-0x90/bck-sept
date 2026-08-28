import hashlib
import hmac
import os
import re
import secrets
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(HERE, "companyemail.db"))
COMPANY_DOMAIN = "apple.test"
EMAIL_LOCAL_RE = re.compile(r"^[A-Za-z0-9._+-]{1,64}$")


def mail_validator(email: str) -> bool:
    if not isinstance(email, str):
        return False
    value = email.strip()
    if len(value) > 254 or any(c in value for c in "\r\n\0"):
        return False
    local, sep, domain = value.rpartition("@")
    return bool(sep and EMAIL_LOCAL_RE.fullmatch(local) and domain.lower() == COMPANY_DOMAIN)


def connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                team_id INTEGER NOT NULL REFERENCES teams(id),
                team_email TEXT NOT NULL
            );
            """
        )
        conn.executemany(
            "INSERT OR IGNORE INTO teams(id, name) VALUES (?, ?)",
            [(1, "mango"), (2, "nightowls"), (3, "pixelpals"), (4, "coffee")],
        )


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        actual = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
        )
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def list_teams():
    with connect() as conn:
        return conn.execute("SELECT id, name FROM teams ORDER BY id").fetchall()


def user_by_id(user_id):
    if not user_id:
        return None
    with connect() as conn:
        return conn.execute(
            """SELECT users.id, users.username, users.email, users.team_id,
                      users.team_email, teams.name AS team_name
               FROM users
               JOIN teams ON teams.id = users.team_id
               WHERE users.id = ?""",
            (user_id,),
        ).fetchone()


def create_user(username, email, password, team_id, team_email):
    if not mail_validator(email):
        raise ValueError("Invalid company user email")
    if not mail_validator(team_email):
        raise ValueError("Invalid company team email")

    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO users(username, email, password_hash, team_id, team_email)
               VALUES (?, ?, ?, ?, ?)""",
            (username, email.lower(), hash_password(password), team_id, team_email.lower()),
        )
        return cur.lastrowid


def login_user(username, password):
    with connect() as conn:
        user = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user["id"]


def team_filter(user_team_id, query):
    sql = (
        f"SELECT id, name FROM teams "
        f"WHERE name LIKE '%{query}%' AND id = {user_team_id} "
        "ORDER BY name LIMIT 8"
    )
    with connect() as conn:
        return conn.execute(sql).fetchall()


def rename_team(team_id, new_name):
    with connect() as conn:
        conn.execute("UPDATE teams SET name = ? WHERE id = ?", (new_name, team_id))

def get_team_name(team_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT name FROM teams WHERE id = ?",
            (team_id,),
        ).fetchone()

    return row["name"] if row else None
