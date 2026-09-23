# Task API

Task API is a simple REST API for managing tasks.

The service allows users to create, view, update, and delete tasks.

## Technologies

- Python 3.12
- FastAPI
- Uvicorn
- Pytest
- Docker

## API Endpoints

- `GET /api/tasks` — get all tasks
- `GET /api/tasks/{task_id}` — get a task by ID
- `POST /api/tasks` — create a new task
- `PUT /api/tasks/{task_id}` — update a task
- `DELETE /api/tasks/{task_id}` — delete a task

## Run tests

```bash
pytest -v
```

## Build Docker image

```bash
docker build -t task-api .
```

## Run Docker container

```bash
docker run -p 8000:8000 task-api
```

After starting the container, the API is available at:

`http://localhost:8000`

Swagger UI:

`http://localhost:8000/docs`