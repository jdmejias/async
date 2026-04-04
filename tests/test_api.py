import os
import sys

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_create_order_publishes(monkeypatch):
    """Verify creating an order generates a task and publishes the correct message."""
    captured = {}

    def fake_create_task():
        return "task-123"

    def fake_publish(routing_key, message):
        captured["routing_key"] = routing_key
        captured["message"] = message

    monkeypatch.setattr(api, "create_task", fake_create_task)
    monkeypatch.setattr(api, "_publish", fake_publish)

    resp = client.post("/orders", json={"foo": "bar"})
    assert resp.status_code == 202
    data = resp.json()
    assert data["taskId"] == "task-123"
    assert captured["routing_key"] == "tasks.createOrder"
    assert captured["message"]["type"] == "CREATE_ORDER"


def test_get_task_status_variants(monkeypatch):
    """Verify task status endpoint returns correct responses for PENDING, FAILED and COMPLETED."""
    # PENDING
    monkeypatch.setattr(api, "get_task", lambda tid: ("t1", "PENDING", None, None))
    r = client.get("/tasks/t1")
    assert r.status_code == 200 and r.json()["status"] == "PENDING"

    # FAILED
    monkeypatch.setattr(api, "get_task", lambda tid: ("t2", "FAILED", None, "err"))
    r = client.get("/tasks/t2")
    assert r.status_code == 200 and r.json()["status"] == "FAILED"

    # COMPLETED -> redirect
    monkeypatch.setattr(api, "get_task", lambda tid: ("t3", "COMPLETED", {"orderId": "o1"}, None))
    r = client.get("/tasks/t3", follow_redirects=False)
    assert r.status_code == 302


def test_get_order_endpoint(monkeypatch):
    """Verify fetching an order returns stored payload and metadata."""
    monkeypatch.setattr(api, "fetch_order", lambda oid: ("o1", {"a": 1}, None, False))
    r = client.get("/orders/o1")
    assert r.status_code == 200
    assert r.json()["orderId"] == "o1"


def test_list_orders(monkeypatch):
    """Verify listing orders returns the whole collection."""
    monkeypatch.setattr(api, "fetch_orders", lambda: [("o1", {"a": 1}, None, False)])
    r = client.get("/orders")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["orders"][0]["orderId"] == "o1"


def test_whoami(monkeypatch):
    """Verify the API exposes the current instance identity."""
    monkeypatch.setattr(api, "_get_instance_identity", lambda: ("ip-10-0-1-10", ["10.0.1.10"]))
    r = client.get("/whoami")
    assert r.status_code == 200
    body = r.json()
    assert body["hostname"] == "ip-10-0-1-10"
    assert body["primaryIp"] == "10.0.1.10"
