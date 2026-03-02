import json
import sys
import os
from types import SimpleNamespace

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import worker


def test_handle_create_and_callback(monkeypatch):
    """Ensure create handler inserts an order and callback acknowledges the message."""
    recorded = {}

    def fake_insert_order(payload):
        recorded['payload'] = payload
        return 'order-1'

    def fake_set_task(task_id, status, result=None, error=None):
        recorded.setdefault('tasks', []).append((task_id, status, result, error))

    monkeypatch.setattr(worker, 'insert_order', fake_insert_order)
    monkeypatch.setattr(worker, 'set_task', fake_set_task)

    # test handler directly
    worker._handle_create('t1', {'x': 1})
    assert recorded['tasks'][-1][1] == 'COMPLETED'

    # test callback path for CREATE_ORDER without custom classes
    acked = []
    ch = SimpleNamespace()
    ch.basic_ack = lambda delivery_tag=None: acked.append(delivery_tag)
    method = SimpleNamespace(delivery_tag=99)
    msg = {'taskId': 't2', 'type': 'CREATE_ORDER', 'payload': {'z': 2}}
    worker.callback(ch, method, None, json.dumps(msg).encode())
    assert acked == [99]
    assert any(t[0] == 't2' for t in recorded['tasks'])


def test_handle_update_and_delete(monkeypatch):
    """Ensure update and delete handlers perform DB actions and mark tasks COMPLETED."""
    recorded = {}

    def fake_update_order(order_id, payload):
        recorded['update'] = (order_id, payload)
        return True

    def fake_soft_delete_order(order_id):
        recorded['delete'] = order_id
        return True

    def fake_set_task(task_id, status, result=None, error=None):
        recorded.setdefault('tasks', []).append((task_id, status, result, error))

    monkeypatch.setattr(worker, 'update_order', fake_update_order)
    monkeypatch.setattr(worker, 'soft_delete_order', fake_soft_delete_order)
    monkeypatch.setattr(worker, 'set_task', fake_set_task)

    worker._handle_update('t3', 'o1', {'a': 9})
    assert recorded['update'][0] == 'o1'
    assert recorded['tasks'][-1][1] == 'COMPLETED'

    worker._handle_delete('t4', 'o2')
    assert recorded['delete'] == 'o2'
    assert recorded['tasks'][-1][1] == 'COMPLETED'
