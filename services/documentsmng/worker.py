import contextvars
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Dict, Optional

current_distribution_tenant: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_distribution_tenant", default=None
)


class Storage:
    def __init__(self, base_dir: Path = Path("/tmp/runtime/documentsmng/exports")):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.in_memory_store: Dict[str, str] = {}

    def save(self, destination: str, data: str) -> None:
        if destination.startswith("timeout:") or destination.startswith("fail:"):
            raise TimeoutError("Storage backend timeout")
        self.in_memory_store[destination] = data
        dest_path = self.base_dir / destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(data, encoding="utf-8")

    def read(self, destination: str) -> Optional[str]:
        if destination in self.in_memory_store:
            return self.in_memory_store[destination]
        dest_path = self.base_dir / destination
        if dest_path.exists():
            return dest_path.read_text(encoding="utf-8")
        return None


def execute_job(conn: sqlite3.Connection, job_id: int, storage: Storage) -> bool:
    job = conn.execute(
        "SELECT id, document_id, requester_id, destination FROM export_jobs WHERE id = ? AND status = 'pending'",
        (job_id,),
    ).fetchone()
    if not job:
        return False

    doc = conn.execute(
        "SELECT id, title, content FROM documents WHERE id = ?",
        (job["document_id"],),
    ).fetchone()
    if not doc:
        conn.execute("UPDATE export_jobs SET status = 'failed' WHERE id = ?", (job_id,))
        return False

    payload = f"Title: {doc['title']}\nContent: {doc['content']}"
    storage.save(job["destination"], payload)

    conn.execute("UPDATE export_jobs SET status = 'completed' WHERE id = ?", (job_id,))
    return True


def process_pending_jobs(conn: sqlite3.Connection, storage: Storage, current_time: Optional[str] = None) -> int:
    if current_time is None:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    else:
        now_str = current_time

    jobs = conn.execute(
        """
        SELECT id FROM export_jobs
        WHERE status = 'pending' AND (execute_at IS NULL OR execute_at <= ?)
        ORDER BY id ASC
        """,
        (now_str,),
    ).fetchall()

    processed = 0
    for job in jobs:
        if execute_job(conn, job["id"], storage):
            processed += 1
    return processed


def get_scoped_distribution_document(conn: sqlite3.Connection, doc_id: int):
    t_id = current_distribution_tenant.get()
    if t_id is not None:
        return conn.execute(
            "SELECT id, title, content, tenant_id FROM documents WHERE id = ? AND tenant_id = ?",
            (doc_id, t_id),
        ).fetchone()
    return conn.execute(
        "SELECT id, title, content, tenant_id FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()


def execute_distribution_task(conn: sqlite3.Connection, task_id: int, storage: Storage) -> bool:
    task = conn.execute(
        "SELECT id, document_id, requester_id, tenant_id, target_endpoint FROM distribution_tasks WHERE id = ? AND status = 'pending'",
        (task_id,),
    ).fetchone()
    if not task:
        return False

    try:
        if task["tenant_id"] is not None:
            current_distribution_tenant.set(task["tenant_id"])

        doc = get_scoped_distribution_document(conn, task["document_id"])
        if not doc:
            conn.execute("UPDATE distribution_tasks SET status = 'failed' WHERE id = ?", (task_id,))
            current_distribution_tenant.set(None)
            return False

        payload = f"Title: {doc['title']}\nContent: {doc['content']}"
        storage.save(task["target_endpoint"], payload)

        conn.execute("UPDATE distribution_tasks SET status = 'completed' WHERE id = ?", (task_id,))
        current_distribution_tenant.set(None)
        return True
    except Exception:
        conn.execute("UPDATE distribution_tasks SET status = 'failed' WHERE id = ?", (task_id,))
        return False


def process_pending_distribution_tasks(conn: sqlite3.Connection, storage: Storage, current_time: Optional[str] = None) -> int:
    if current_time is None:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    else:
        now_str = current_time

    tasks = conn.execute(
        """
        SELECT id FROM distribution_tasks
        WHERE status = 'pending' AND (scheduled_at IS NULL OR scheduled_at <= ?)
        ORDER BY id ASC
        """,
        (now_str,),
    ).fetchall()

    processed = 0
    for task in tasks:
        if execute_distribution_task(conn, task["id"], storage):
            processed += 1
    return processed
