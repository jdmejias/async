import os
import psycopg
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


@contextmanager
def get_conn():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables and apply any pending column migrations."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # ── tasks ────────────────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id    TEXT        PRIMARY KEY,
                    status     TEXT        NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    result     JSONB,
                    error      TEXT
                )
            """)
            # migrate: add columns that may be missing from older schema
            for col, definition in [
                ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
                ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
            ]:
                cur.execute(
                    f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {col} {definition}"
                )
            # migrate result column to JSONB if it was created as TEXT
            cur.execute("""
                DO $$ BEGIN
                    IF (SELECT data_type FROM information_schema.columns
                        WHERE table_name='tasks' AND column_name='result') = 'text' THEN
                        ALTER TABLE tasks ALTER COLUMN result TYPE JSONB
                            USING CASE WHEN result IS NULL THEN NULL ELSE result::jsonb END;
                    END IF;
                END $$;
            """)

            # ── orders ───────────────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id   TEXT        PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    payload    JSONB       NOT NULL,
                    deleted    BOOLEAN     NOT NULL DEFAULT FALSE
                )
            """)
            # migrate: add columns that may be missing from older schema
            for col, definition in [
                ("deleted", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
            ]:
                cur.execute(
                    f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {definition}"
                )
            # migrate payload column to JSONB if it was created as TEXT
            cur.execute("""
                DO $$ BEGIN
                    IF (SELECT data_type FROM information_schema.columns
                        WHERE table_name='orders' AND column_name='payload') = 'text' THEN
                        ALTER TABLE orders ALTER COLUMN payload TYPE JSONB
                            USING CASE WHEN payload IS NULL THEN NULL ELSE payload::jsonb END;
                    END IF;
                END $$;
            """)

        conn.commit()