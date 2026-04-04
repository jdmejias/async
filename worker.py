import json
import os
import time

import pika

from db import init_db, insert_order, set_task, soft_delete_order, update_order

RABBIT_URL = os.environ.get("RABBIT_URL")
EXCHANGE = os.environ.get("EXCHANGE", "orders")
QUEUE = os.environ.get("QUEUE", "orders.queue")

ROUTING_KEYS = ["tasks.createOrder", "tasks.updateOrder", "tasks.deleteOrder"]


def _handle_create(task_id: str, payload: dict):
    """Insert a new order and mark the task as COMPLETED."""
    order_id = insert_order(payload)
    set_task(task_id, "COMPLETED", result={"orderId": order_id, "resourceUri": f"/orders/{order_id}"})


def _handle_update(task_id: str, order_id: str, payload: dict):
    """Update an order's payload; mark the task COMPLETED or FAILED."""
    ok = update_order(order_id, payload)
    if not ok:
        set_task(task_id, "FAILED", error=f"Order {order_id} not found or deleted")
        return
    set_task(task_id, "COMPLETED", result={"orderId": order_id, "resourceUri": f"/orders/{order_id}"})


def _handle_delete(task_id: str, order_id: str):
    """Soft-delete an order and mark the task COMPLETED or FAILED."""
    ok = soft_delete_order(order_id)
    if not ok:
        set_task(task_id, "FAILED", error=f"Order {order_id} not found or already deleted")
        return
    set_task(task_id, "COMPLETED", result={"orderId": order_id, "deleted": True})


def callback(ch, method, properties, body):
    """Process a RabbitMQ message, route to the correct handler, and ack."""
    msg = json.loads(body.decode())
    task_id = msg.get("taskId")
    msg_type = msg.get("type")

    print(f"[worker] received {msg_type} task={task_id}")
    try:
        set_task(task_id, "IN_PROGRESS")
        time.sleep(1)
        if msg_type == "CREATE_ORDER":
            _handle_create(task_id, msg.get("payload", {}))
        elif msg_type == "UPDATE_ORDER":
            _handle_update(task_id, msg["orderId"], msg.get("payload", {}))
        elif msg_type == "DELETE_ORDER":
            _handle_delete(task_id, msg["orderId"])
        else:
            set_task(task_id, "FAILED", error=f"Unknown message type: {msg_type}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[worker] done {msg_type} task={task_id}")
    except Exception as exc:
        print(f"[worker] error processing {msg_type}: {exc}")
        set_task(task_id, "FAILED", error=str(exc))
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    """Initialize DB, connect to RabbitMQ and start consuming messages."""
    init_db()
    params = pika.URLParameters(RABBIT_URL)
    deadline = time.time() + 300
    while True:
        try:
            connection = pika.BlockingConnection(params)
            break
        except pika.exceptions.AMQPConnectionError:
            if time.time() > deadline:
                raise
            print("[worker] RabbitMQ not ready, retrying in 1s...")
            time.sleep(1)
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)
    for rk in ROUTING_KEYS:
        channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=rk)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=callback)
    print(f"[worker] listening on queue '{QUEUE}' (exchange '{EXCHANGE}')")
    channel.start_consuming()


if __name__ == "__main__":
    main()
