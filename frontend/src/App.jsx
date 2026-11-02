
import { useEffect, useState } from 'react'
import './App.css'

const API = '/api/tasks'

function App() {
  const [tasks, setTasks] = useState([])
  const [title, setTitle] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function loadTasks() {
    try {
      const response = await fetch(API)
      if (!response.ok) throw new Error('Failed to load tasks')
      setTasks(await response.json())
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [])

  async function saveTask(event) {
    event.preventDefault()
    if (!title.trim()) return

    const existing = tasks.find(task => task.id === editingId)
    const task = {
      id: editingId ?? Math.max(0, ...tasks.map(t => t.id)) + 1,
      title: title.trim(),
      completed: existing?.completed ?? false,
    }

    try {
      const response = await fetch(
        editingId === null ? API : `${API}/${editingId}`,
        {
          method: editingId === null ? 'POST' : 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(task),
        }
      )
      if (!response.ok) throw new Error('Failed to save task')
      setTitle('')
      setEditingId(null)
      await loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteTask(id) {
    try {
      const response = await fetch(`${API}/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete task')
      await loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  async function toggleTask(task) {
    try {
      const response = await fetch(`${API}/${task.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...task,
          completed: !task.completed,
        }),
      })
      if (!response.ok) throw new Error('Failed to update task')
      await loadTasks()
    } catch (err) {
      setError(err.message)
    }
  }

  function editTask(task) {
    setEditingId(task.id)
    setTitle(task.title)
  }

  return (
    <main className="container">
      <header>
        <h1>Task Manager</h1>
        <p>Manage your tasks with React and FastAPI</p>
      </header>

      <form onSubmit={saveTask} className="task-form">
        <input
          value={title}
          onChange={event => setTitle(event.target.value)}
          placeholder="Enter task title..."
          required
        />
        <button type="submit">
          {editingId === null ? 'Add Task' : 'Save Changes'}
        </button>
        {editingId !== null && (
          <button type="button" onClick={() => {
            setEditingId(null)
            setTitle('')
          }}>
            Cancel
          </button>
        )}
      </form>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p>Loading tasks...</p>
      ) : (
        <section className="task-list">
          {tasks.length === 0 && <p>No tasks yet.</p>}
          {tasks.map(task => (
            <article key={task.id} className="task">
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task)}
              />
              <span className={task.completed ? 'completed' : ''}>
                {task.title}
              </span>
              <button onClick={() => editTask(task)}>Edit</button>
              <button
                className="delete"
                onClick={() => deleteTask(task.id)}
              >
                Delete
              </button>
            </article>
          ))}
        </section>
      )}

      <footer>
        Total: {tasks.length} | Completed: {
          tasks.filter(task => task.completed).length
        }
      </footer>
    </main>
  )
}

export default App
