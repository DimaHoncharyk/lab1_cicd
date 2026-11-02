import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base, TaskDB


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add_all([
            TaskDB(
                id=1,
                title="Learn FastAPI",
                completed=False,
            ),
            TaskDB(
                id=2,
                title="Create REST API",
                completed=True,
            ),
        ])
        db.commit()

    yield


def test_get_tasks():
    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_task():
    response = client.get("/api/tasks/1")

    assert response.status_code == 200
    assert response.json()["title"] == "Learn FastAPI"


def test_get_nonexistent_task():
    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_create_task():
    response = client.post(
        "/api/tasks",
        json={
            "id": 3,
            "title": "Test SQLite",
            "completed": False,
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Test SQLite"

    get_response = client.get("/api/tasks/3")
    assert get_response.status_code == 200


def test_update_task():
    response = client.put(
        "/api/tasks/1",
        json={
            "id": 1,
            "title": "Updated Task",
            "completed": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert response.json()["title"] == "Updated Task"


def test_delete_task():
    response = client.delete("/api/tasks/1")

    assert response.status_code == 200

    get_response = client.get("/api/tasks/1")
    assert get_response.status_code == 404
