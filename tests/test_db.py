import sys
import os
import json
import uuid

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db


class FakeCursor:
    def __init__(self):
        self.queries = []
        self.fetchone_result = None

    def execute(self, sql, params=None):
        self.queries.append((sql.strip(), params))

    def fetchone(self):
        return self.fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        pass


def test_create_task_and_set_task(monkeypatch):
    """Verify creating tasks issues an INSERT and updating issues an UPDATE."""
    cur = FakeCursor()
    conn = FakeConn(cur)

    monkeypatch.setattr(db.psycopg, 'connect', lambda url=None: conn)

    tid = db.create_task()
    assert isinstance(tid, str)
    # create_task should have executed an INSERT
    assert any('INSERT INTO tasks' in q[0] for q in cur.queries)

    # test set_task issues UPDATE
    cur.queries.clear()
    db.set_task('t1', 'COMPLETED', result={'a': 1}, error=None)
    assert any('UPDATE tasks SET status' in q[0] for q in cur.queries)


def test_order_crud(monkeypatch):
    """Verify order INSERT, fetch (None), UPDATE behavior and soft-delete."""
    cur = FakeCursor()
    conn = FakeConn(cur)
    monkeypatch.setattr(db.psycopg, 'connect', lambda url=None: conn)

    # insert_order
    cur.queries.clear()
    oid = db.insert_order({'x': 1})
    assert any('INSERT INTO orders' in q[0] for q in cur.queries)

    # fetch_order returns None when nothing set
    cur.fetchone_result = None
    res = db.fetch_order('nope')
    assert res is None

    # update_order when not exists
    cur.fetchone_result = None
    ok = db.update_order('o1', {'a': 2})
    assert ok is False

    # update_order when exists
    cur.fetchone_result = ('o1',)
    cur.queries.clear()
    ok = db.update_order('o1', {'a': 2})
    assert ok is True
    assert any('UPDATE orders SET payload' in q[0] for q in cur.queries)

    # soft_delete_order when exists
    cur.fetchone_result = ('o2',)
    cur.queries.clear()
    ok = db.soft_delete_order('o2')
    assert ok is True
    assert any('UPDATE orders SET deleted' in q[0] for q in cur.queries)
