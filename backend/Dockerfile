FROM python:3.11-slim

WORKDIR /app

# system deps for IfcOpenShell (optional, fallback works without)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY sample-ifc ./sample-ifc
COPY frontend ./frontend
COPY prompts ./prompts
COPY run.sh ./run.sh

EXPOSE 8000
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
