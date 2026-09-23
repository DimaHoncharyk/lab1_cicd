from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
def test_get_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
def test_get_task():
    response = client.get("/api/tasks/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["title"] == "Learn FastAPI"
def test_get_nonexistent_task():
    response = client.get("/api/tasks/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"