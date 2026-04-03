import os
import time
import uuid

import httpx


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
INTERVAL_SECONDS = int(os.getenv("PRODUCER_INTERVAL_SECONDS", "10"))


def wait_for_api(client: httpx.Client, timeout_seconds: int = 60) -> None:
    """Wait until the API is reachable before producing synthetic traffic."""
    deadline = time.time() + timeout_seconds
    while True:
        try:
            resp = client.get(f"{API_BASE_URL}/docs")
            if resp.status_code == 200:
                print("[producer] API is ready")
                return
        except httpx.HTTPError:
            pass

        if time.time() > deadline:
            raise TimeoutError("API was not reachable before timeout")

        print("[producer] waiting for API...")
        time.sleep(2)


def build_payload(counter: int) -> dict:
    """Create a deterministic synthetic order payload with unique fields."""
    return {
        "customerId": f"synthetic-{counter:05d}",
        "items": [{"product": "demo-widget", "quantity": (counter % 5) + 1}],
        "total": round(9.99 + (counter % 10), 2),
        "traceId": str(uuid.uuid4()),
    }


def main() -> None:
    """Send synthetic API requests every fixed interval."""
    print(f"[producer] target={API_BASE_URL} interval={INTERVAL_SECONDS}s")
    counter = 0

    with httpx.Client(timeout=10.0) as client:
        wait_for_api(client)

        while True:
            counter += 1
            payload = build_payload(counter)
            try:
                resp = client.post(f"{API_BASE_URL}/orders", json=payload)
                if resp.status_code == 202:
                    body = resp.json()
                    print(f"[producer] sent order #{counter} taskId={body.get('taskId')}")
                else:
                    print(f"[producer] unexpected status={resp.status_code} body={resp.text}")
            except httpx.HTTPError as exc:
                print(f"[producer] request failed: {exc}")

            time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()