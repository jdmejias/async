**IOT Async Request Reply**

- **Authors:** Nestor Ortiz, Jhon Mejías
- **Description:** Minimal demo of an asynchronous request–reply pattern: an HTTP API, background worker, PostgreSQL and RabbitMQ.

**Requirements:** Docker and Docker Compose.
- **Install (Windows):** https://docs.docker.com/desktop/install/windows-install/
- **Install (macOS):** https://docs.docker.com/desktop/install/mac-install/
- **Install (Linux):** https://docs.docker.com/engine/install/
- **Compose install:** https://docs.docker.com/compose/install/

## Quick Commands

**Start everything:**
```bash
docker-compose up --build -d
```

**Run unit tests:**
```bash
docker-compose exec -it api pytest
```

**View logs on api:**
```bash
docker-compose logs -f api
```

**View logs on worker:**
```bash
docker-compose logs -f worker
```

**View logs on db:**
```bash
docker-compose logs -f db
```

**Refresh containers (rebuild):**
```bash
docker-compose up --build -d
```

**Stop and remove images:**
```bash
docker-compose down --rmi all
```

## API Usage

Open **http://localhost:8000/docs** to access the interactive API interface powered by FastAPI/Swagger UI.

This interface allows you to explore all available endpoints and test them directly from your browser.

### Creating Orders

1. On the Swagger UI, find the **POST /orders** endpoint
2. Click "Try it out"
3. In the request body, enter your order payload in JSON format:
   ```json
   {
     "customerId": "cust-123",
     "items": [
       {"product": "widget", "quantity": 5}
     ],
     "total": 99.99
   }
   ```
4. Click "Execute"
5. You'll receive a response with a `taskId` and `statusUrl` to track the order creation

The order creation is processed asynchronously in the background. Save the `taskId` to check its status.

### Checking Task Status

1. Find the **GET /tasks/{task_id}** endpoint in Swagger UI
2. Click "Try it out"
3. Enter the `taskId` from the previous step
4. Click "Execute"
5. Check the response:
   - **PENDING/IN_PROGRESS:** Task is still being processed
   - **SUCCESS:** Task completed successfully. For order creation, you'll be redirected to the order details
   - **FAILED:** Task failed with an error message

### Querying Orders

1. Find the **GET /orders/{order_id}** endpoint
2. Click "Try it out"
3. Enter your `order_id`
4. Click "Execute"
5. View the complete order details including payload and creation timestamp

### Updating Orders

1. Find the **PUT /orders/{order_id}** endpoint
2. Click "Try it out"
3. Enter the `order_id` you want to update
4. Provide the updated payload in the request body
5. Click "Execute"
6. Use the returned `taskId` to track the update status

### Deleting Orders

1. Find the **DELETE /orders/{order_id}** endpoint
2. Click "Try it out"
3. Enter the `order_id` to delete
4. Click "Execute"
5. Use the returned `taskId` to track the deletion status
