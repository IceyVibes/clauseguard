# ClauseGuard - container image for the FastAPI backend and demo server.
# Educational hackathon prototype. OCI-compatible; works with Docker and Podman.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY demo demo

RUN mkdir -p backend/models \
    && addgroup --system clauseguard \
    && adduser --system --ingroup clauseguard --home /app clauseguard \
    && chown -R clauseguard:clauseguard /app

USER clauseguard

# Documentation only; actual port mapping happens via `docker run -p` / compose.
EXPOSE 8000
EXPOSE 5500

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
