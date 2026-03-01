**Proyecto: Async Demo / Async Demo Project**

**Descripción / Description**
- **ES:** Proyecto para mostrar una arquitectura asíncrona con microservicios: una API HTTP, un worker de tareas en segundo plano, una base de datos PostgreSQL y un broker RabbitMQ.
- **EN:** project demonstrating an asynchronous microservice architecture: an HTTP API, a background worker, a PostgreSQL database, and a RabbitMQ broker.

**Arquitectura y Contenedores / Architecture & Containers**
- **db:** Contenedor basado en `postgres:15`. Proporciona la persistencia de datos. Volumen: `db_data`.
- **rabbit:** Contenedor basado en `rabbitmq:3-management`. Actúa como broker de mensajería (puerto de cliente AMQP 5672 y panel de administración 15672).
- **api:** Servicio construido a partir del `Dockerfile`. Expone la API HTTP (uvicorn) en el puerto `8000`. Usa variables de entorno desde `.env.example` y depende de `db` y `rabbit`.
- **worker:** Servicio construido desde el mismo `Dockerfile` (misma imagen), pero se ejecuta con `python worker.py` para procesar tareas en segundo plano. Está desacoplado de la API y se comunica mediante RabbitMQ.

Separación de microservicios en contenedores:
- La API y el worker se despliegan en contenedores separados aunque puedan compartir la misma imagen de base. Esto permite escalar y desplegar cada microservicio de forma independiente y ejecutar comandos distintos (ej. `uvicorn` vs `python worker.py`).
- La base de datos y el broker son servicios gestionados por imágenes oficiales y corren en contenedores independientes para mantener separación de responsabilidades.

**Cómo ejecutar (Docker) / How to run (Docker)**
- Requisitos: `docker` y `docker-compose` instalados.
- Levantar los servicios:

```bash
docker-compose up -d
```

- Ver logs:

```bash
docker-compose logs -f api
docker-compose logs -f worker
```

- Parar y eliminar (incluye volumen si quieres resetear la BD):

```bash
docker-compose down -v
```

**Ejecución en desarrollo sin Docker / Local development (venv)**
- Crear y activar un entorno virtual (Windows PowerShell ejemplo):

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Ejecutar la API localmente:

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

- Ejecutar el worker localmente:

```bash
python worker.py
```

**Variables de entorno / Environment variables**
- Usa el archivo de ejemplo `.env.example` para definir las variables necesarias (conexión a la BD, credenciales de RabbitMQ, etc.). Cuando uses Docker, `docker-compose.yml` carga `env_file: .env.example` para `api` y `worker`.

**Puertos expuestos / Exposed ports**
- `8000` — API HTTP
- `5432` — PostgreSQL (mapeado para acceso local)
- `5672` — RabbitMQ (AMQP)
- `15672` — RabbitMQ Management UI

**Estructura del repositorio / Repository structure**
- `api.py` — Código de la API.
- `worker.py` — Lógica del trabajador de tareas en segundo plano.
- `db.py` — Módulo relacionado con la base de datos.
- `Dockerfile` — Define la imagen usada por `api` y `worker`.
- `docker-compose.yml` — Orquesta los servicios (db, rabbit, api, worker).
- `requirements.txt` — Dependencias Python.

**Operaciones útiles / Useful commands**
- Reconstruir imágenes (después de cambios):

```bash
docker-compose build --no-cache
```

- Acceder a un shell dentro del contenedor API:

```bash
docker-compose exec api sh
```

**Notas / Notes**
- Aunque `api` y `worker` usan la misma imagen como base, cada servicio se ejecuta con un comando distinto — esto permite separar claramente responsabilidades y escalado.
- Si cambias el esquema de la base de datos considera añadir migraciones y un paso de inicialización.

**Contacto / Contact**
- Autor / Author: Nestor Ortiz (documentado según su comentario).

---

Si deseas, puedo:
- Añadir ejemplos de `.env` concretos (sin credenciales reales).
- Incluir instrucciones de migraciones de base de datos.
- Crear un `README` más corto para despliegue en producción.
