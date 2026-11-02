from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import TaskDB


app = FastAPI(
    title="Task API",
    description="REST API for managing tasks with PostgreSQL",
    version="2.0.0"
)


class Task(BaseModel):
    id: int
    title: str
    completed: bool = False


@app.get("/")
def home():
    return {"message": "Task API is running"}


@app.get("/api/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return db.query(TaskDB).order_by(TaskDB.id).all()


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskDB, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@app.post("/api/tasks", status_code=201)
def create_task(task: Task, db: Session = Depends(get_db)):
    if db.get(TaskDB, task.id) is not None:
        raise HTTPException(
            status_code=400,
            detail="Task with this ID already exists"
        )

    new_task = TaskDB(
        id=task.id,
        title=task.title,
        completed=task.completed
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


@app.put("/api/tasks/{task_id}")
def update_task(
    task_id: int,
    updated_task: Task,
    db: Session = Depends(get_db)
):
    task = db.get(TaskDB, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if updated_task.id != task_id:
        raise HTTPException(
            status_code=400,
            detail="Task ID cannot be changed"
        )

    task.title = updated_task.title
    task.completed = updated_task.completed

    db.commit()
    db.refresh(task)

    return task


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskDB, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    deleted_task = {
        "id": task.id,
        "title": task.title,
        "completed": task.completed
    }

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted successfully",
        "task": deleted_task
    }
