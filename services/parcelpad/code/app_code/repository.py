from psycopg.types.json import Jsonb

from .db import connect_db


class Repository:
    def list_records(self):
        with connect_db() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, flow_type, stage, status, payload
                FROM flow_records
                ORDER BY created_at, id
                """
            )
            return list(cur.fetchall())

    def get_record(self, flow_type, record_id):
        with connect_db() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, flow_type, stage, status, payload
                FROM flow_records
                WHERE flow_type = %s AND id = %s
                """,
                (flow_type, record_id),
            )
            return cur.fetchone()

    def set_stage(self, record_id, stage, status=None):
        with connect_db() as conn, conn.cursor() as cur:
            if status is None:
                cur.execute(
                    "UPDATE flow_records SET stage = %s WHERE id = %s",
                    (stage, record_id),
                )
            else:
                cur.execute(
                    "UPDATE flow_records SET stage = %s, status = %s WHERE id = %s",
                    (stage, status, record_id),
                )

    def save_payload(self, record_id, payload, *, stage=None, status=None):
        with connect_db() as conn, conn.cursor() as cur:
            if stage is None and status is None:
                cur.execute(
                    "UPDATE flow_records SET payload = %s WHERE id = %s",
                    (Jsonb(payload), record_id),
                )
            elif stage is None:
                cur.execute(
                    "UPDATE flow_records SET payload = %s, status = %s WHERE id = %s",
                    (Jsonb(payload), status, record_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE flow_records
                    SET payload = %s, stage = %s, status = %s
                    WHERE id = %s
                    """,
                    (Jsonb(payload), stage, status, record_id),
                )

    def reference_exists(self, category, value):
        with connect_db() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM reference_values
                WHERE category = %s AND value = %s AND active = TRUE
                """,
                (category, value),
            )
            return cur.fetchone() is not None

    def reference_meta(self, category, value):
        with connect_db() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT meta
                FROM reference_values
                WHERE category = %s AND value = %s AND active = TRUE
                """,
                (category, value),
            )
            row = cur.fetchone()
            return row["meta"] if row else None
