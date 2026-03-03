import json
import os

import pika
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from db import create_task, fetch_order, get_task, init_db

RABBIT_URL = os.environ.get("RABBIT_URL")
EXCHANGE = os.environ.get("EXCHANGE", "orders")
DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI()


@app.on_event("startup")
def startup():
    """Initialize the database when the application starts.

    Skip initialization when `DATABASE_URL` is not set so tests can import
    the app without requiring full runtime environment variables.
    """
    if DATABASE_URL:
        init_db()


def _publish(routing_key: str, message: dict):
    """Publish a persistent JSON message to the configured RabbitMQ exchange."""
    params = pika.URLParameters(RABBIT_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(message).encode(),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    conn.close()


@app.post("/orders", status_code=202)
def create_order(payload: dict):
    """Create a background task to create an order and publish the request."""
    task_id = create_task()
    _publish("tasks.createOrder", {"taskId": task_id, "type": "CREATE_ORDER", "payload": payload})
    return {"taskId": task_id, "statusUrl": f"/tasks/{task_id}"}


@app.put("/orders/{order_id}", status_code=202)
def update_order(order_id: str, payload: dict):
    """Create a background task to update an order and publish the request."""
    task_id = create_task()
    _publish("tasks.updateOrder", {"taskId": task_id, "type": "UPDATE_ORDER", "orderId": order_id, "payload": payload})
    return {"taskId": task_id, "statusUrl": f"/tasks/{task_id}"}


@app.delete("/orders/{order_id}", status_code=202)
def delete_order(order_id: str):
    """Create a background task to delete an order and publish the request."""
    task_id = create_task()
    _publish("tasks.deleteOrder", {"taskId": task_id, "type": "DELETE_ORDER", "orderId": order_id})
    return {"taskId": task_id, "statusUrl": f"/tasks/{task_id}"}


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """Return the status and result (or error) for a background task."""
    row = get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    tid, status, result, error = row
    if status in ("PENDING", "IN_PROGRESS"):
        return JSONResponse(status_code=200, content={"taskId": tid, "status": status})
    if status == "FAILED":
        return JSONResponse(status_code=200, content={"taskId": tid, "status": status, "error": error})
    if result and isinstance(result, dict) and "orderId" in result:
        return RedirectResponse(url=f"/orders/{result['orderId']}", status_code=302)
    return JSONResponse(status_code=200, content={"taskId": tid, "status": status, "result": result})


@app.get("/orders/{order_id}")
def get_order_endpoint(order_id: str):
    """Return the stored order payload for a given `order_id` if present."""
    row = fetch_order(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    oid, payload, created_at, deleted = row
    if deleted:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"orderId": oid, "payload": payload, "createdAt": created_at.isoformat() if created_at else None}
