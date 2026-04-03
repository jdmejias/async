import json
import os
import time
import uuid
from contextlib import contextmanager

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")


@contextmanager
def get_conn():
    """Context manager returning a new database connection.

    Usage:
        with get_conn() as conn:
            ...
    """
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def init_db(timeout: int = 30, delay: float = 1.0):
    """Create required tables, retrying until the database is ready.

    This ensures the application can call initialization during container
    startup even if Postgres is still coming online.
    """
    deadline = time.time() + timeout
    while True:
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # Serialize startup DDL across services (api/worker) to avoid
                    # concurrent CREATE TABLE races on first boot.
                    cur.execute("SELECT pg_advisory_lock(hashtext('async_init_db_v1'))")
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            task_id    TEXT PRIMARY KEY,
                            status     TEXT NOT NULL DEFAULT 'PENDING',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            result     JSONB,
                            error      TEXT
                        )
                    """)

                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS orders (
                            order_id   TEXT PRIMARY KEY,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            payload    JSONB NOT NULL,
                            deleted    BOOLEAN NOT NULL DEFAULT FALSE
                        )
                    """)
                    cur.execute("SELECT pg_advisory_unlock(hashtext('async_init_db_v1'))")

                conn.commit()
            break
        except psycopg.OperationalError:
            if time.time() > deadline:
                raise
            time.sleep(delay)


def create_task(conn=None):
    """Create a new PENDING task and return its generated `task_id`."""
    own = conn is None
    if own:
        conn = psycopg.connect(DATABASE_URL)
    try:
        task_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks(task_id, status, created_at, updated_at) VALUES (%s, 'PENDING', NOW(), NOW())",
                (task_id,),
            )
        if own:
            conn.commit()
        return task_id
    finally:
        if own:
            conn.close()


def set_task(task_id: str, status: str, result=None, error=None):
    """Update a task's `status`, `result`, and/or `error` by `task_id`."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET status = %s, result = %s, error = %s, updated_at = NOW() WHERE task_id = %s",
                (status, json.dumps(result) if result is not None else None, error, task_id),
            )
        conn.commit()


def get_task(task_id: str):
    """Return the task row (task_id, status, result, error) or `None` if missing."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT task_id, status, result, error FROM tasks WHERE task_id = %s", (task_id,))
            return cur.fetchone()


def insert_order(payload: dict):
    """Insert a new order and return its generated `order_id`."""
    order_id = str(uuid.uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders(order_id, payload, created_at, deleted) VALUES (%s, %s, NOW(), FALSE)",
                (order_id, json.dumps(payload)),
            )
        conn.commit()
    return order_id


def fetch_order(order_id: str):
    """Fetch an order row (order_id, payload, created_at, deleted) or `None`."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT order_id, payload, created_at, deleted FROM orders WHERE order_id = %s", (order_id,))
            return cur.fetchone()


def update_order(order_id: str, payload: dict):
    """Update an existing order's payload. Return True if updated, False if not found."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT order_id FROM orders WHERE order_id = %s AND deleted = FALSE", (order_id,))
            if not cur.fetchone():
                return False
            cur.execute("UPDATE orders SET payload = %s WHERE order_id = %s", (json.dumps(payload), order_id))
        conn.commit()
    return True


def soft_delete_order(order_id: str):
    """Mark an order as deleted. Return True if marked, False if not found."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT order_id FROM orders WHERE order_id = %s AND deleted = FALSE", (order_id,))
            if not cur.fetchone():
                return False
            cur.execute("UPDATE orders SET deleted = TRUE WHERE order_id = %s", (order_id,))
        conn.commit()
    return True
