import json
import os
import uuid

import pika
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from db import get_conn, init_db

load_dotenv()

RABBIT_URL = os.environ["RABBIT_URL"]
EXCHANGE = os.environ["EXCHANGE"]

app = FastAPI(title="Async Request-Reply Demo")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_task(conn) -> str:
    """Insert a PENDING task row and return its task_id."""
    task_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks(task_id, status, created_at, updated_at)
            VALUES (%s, 'PENDING', NOW(), NOW())
            """,
            (task_id,),
        )
    conn.commit()
    return task_id


def _publish(routing_key: str, message: dict):
    """Publish a persistent JSON message to tasks.exchange."""
    params = pika.URLParameters(RABBIT_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE, exchange_type="direct", durable=True
    )

    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(message).encode(),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


# ---------------------------------------------------------------------------
# POST /orders  — create order asynchronously
# ---------------------------------------------------------------------------

@app.post("/orders", status_code=202)
def create_order(payload: dict):
    with get_conn() as conn:
        task_id = _new_task(conn)

    _publish(
        "tasks.createOrder",
        {"taskId": task_id, "type": "CREATE_ORDER", "payload": payload},
    )
    return {"taskId": task_id, "statusUrl": f"/tasks/{task_id}"}


# ---------------------------------------------------------------------------
# PUT /orders/{orderId}  — update order asynchronously
# ---------------------------------------------------------------------------

@app.put("/orders/{order_id}", status_code=202)
def update_order(order_id: str, payload: dict):
    with get_conn() as conn:
        task_id = _new_task(conn)

    _publish(
        "tasks.updateOrder",
        {
            "taskId": task_id,
            "type": "UPDATE_ORDER",
            "orderId": order_id,
            "payload": payload,
        },
    )
    return {"taskId": task_id, "statusUrl": f"/tasks/{task_id}"}


# ---------------------------------------------------------------------------
# DELETE /orders/{orderId}  — delete order asynchronously
# ---------------------------------------------------------------------------

@app.delete("/orders/{order_id}", status_code=202)
def delete_order(order_id: str):
    with get_conn() as conn:
        task_id = _new_task(conn)

    _publish(
        "tasks.deleteOrder",
        {"taskId": task_id, "type": "DELETE_ORDER", "orderId": order_id},
    )
    return {"taskId": task_id, "statusUrl": f"/tasks/{task_id}"}


# ---------------------------------------------------------------------------
# GET /tasks/{taskId}  — poll task status
# ---------------------------------------------------------------------------

@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT task_id, status, result, error FROM tasks WHERE task_id = %s",
                (task_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    tid, status, result, error = row

    if status in ("PENDING", "IN_PROGRESS"):
        return JSONResponse(status_code=200, content={"taskId": tid, "status": status})

    if status == "FAILED":
        return JSONResponse(
            status_code=200,
            content={"taskId": tid, "status": status, "error": error},
        )

    # COMPLETED
    if result and isinstance(result, dict) and "orderId" in result:
        return RedirectResponse(
            url=f"/orders/{result['orderId']}", status_code=302
        )

    return JSONResponse(
        status_code=200,
        content={"taskId": tid, "status": status, "result": result},
    )


# ---------------------------------------------------------------------------
# GET /orders/{orderId}  — fetch a single order
# ---------------------------------------------------------------------------

@app.get("/orders/{order_id}")
def get_order(order_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT order_id, payload, created_at, deleted FROM orders WHERE order_id = %s",
                (order_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    oid, payload, created_at, deleted = row

    if deleted:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "orderId": oid,
        "payload": payload,
        "createdAt": created_at.isoformat() if created_at else None,
    }
