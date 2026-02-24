import json
import os
import time
import uuid

import pika
from dotenv import load_dotenv

from db import get_conn, init_db

load_dotenv()

RABBIT_URL = os.environ["RABBIT_URL"]
EXCHANGE = os.environ["EXCHANGE"]
QUEUE = os.environ["QUEUE"]

ROUTING_KEYS = [
    "tasks.createOrder",
    "tasks.updateOrder",
    "tasks.deleteOrder",
]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _set_task(task_id: str, status: str, result=None, error=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = %s, result = %s, error = %s, updated_at = NOW()
                WHERE task_id = %s
                """,
                (
                    status,
                    json.dumps(result) if result is not None else None,
                    error,
                    task_id,
                ),
            )
        conn.commit()


# ---------------------------------------------------------------------------
# Business logic per message type
# ---------------------------------------------------------------------------

def _handle_create(task_id: str, payload: dict):
    order_id = str(uuid.uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders(order_id, payload, created_at, deleted)
                VALUES (%s, %s, NOW(), FALSE)
                """,
                (order_id, json.dumps(payload)),
            )
        conn.commit()

    _set_task(
        task_id,
        "COMPLETED",
        result={"orderId": order_id, "resourceUri": f"/orders/{order_id}"},
    )


def _handle_update(task_id: str, order_id: str, payload: dict):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT order_id FROM orders WHERE order_id = %s AND deleted = FALSE",
                (order_id,),
            )
            row = cur.fetchone()
            if not row:
                _set_task(task_id, "FAILED", error=f"Order {order_id} not found or deleted")
                return

            cur.execute(
                "UPDATE orders SET payload = %s WHERE order_id = %s",
                (json.dumps(payload), order_id),
            )
        conn.commit()

    _set_task(
        task_id,
        "COMPLETED",
        result={"orderId": order_id, "resourceUri": f"/orders/{order_id}"},
    )


def _handle_delete(task_id: str, order_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT order_id FROM orders WHERE order_id = %s AND deleted = FALSE",
                (order_id,),
            )
            row = cur.fetchone()
            if not row:
                _set_task(task_id, "FAILED", error=f"Order {order_id} not found or already deleted")
                return

            cur.execute(
                "UPDATE orders SET deleted = TRUE WHERE order_id = %s",
                (order_id,),
            )
        conn.commit()

    _set_task(task_id, "COMPLETED", result={"orderId": order_id, "deleted": True})


# ---------------------------------------------------------------------------
# RabbitMQ callback
# ---------------------------------------------------------------------------

def callback(ch, method, properties, body):
    msg = json.loads(body.decode())
    task_id = msg.get("taskId")
    msg_type = msg.get("type")

    print(f"[worker] received {msg_type} task={task_id}")

    try:
        _set_task(task_id, "IN_PROGRESS")
        time.sleep(1)  # simulate work

        if msg_type == "CREATE_ORDER":
            _handle_create(task_id, msg.get("payload", {}))

        elif msg_type == "UPDATE_ORDER":
            _handle_update(task_id, msg["orderId"], msg.get("payload", {}))

        elif msg_type == "DELETE_ORDER":
            _handle_delete(task_id, msg["orderId"])

        else:
            _set_task(task_id, "FAILED", error=f"Unknown message type: {msg_type}")

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[worker] done {msg_type} task={task_id}")

    except Exception as exc:
        print(f"[worker] error processing {msg_type}: {exc}")
        _set_task(task_id, "FAILED", error=str(exc))
        ch.basic_ack(delivery_tag=method.delivery_tag)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    init_db()

    params = pika.URLParameters(RABBIT_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Declare exchange and queue defensively (idempotent)
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)

    # Bind queue to exchange for all routing keys
    for rk in ROUTING_KEYS:
        channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=rk)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=callback)

    print(f"[worker] listening on queue '{QUEUE}' (exchange '{EXCHANGE}')")
    channel.start_consuming()


if __name__ == "__main__":
    main()
