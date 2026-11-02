FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations/ ./migrations/
COPY models.py .
COPY database.py .

CMD ["alembic", "upgrade", "head"]
