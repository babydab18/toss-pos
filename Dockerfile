FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FRONTEND_DIST=/app/static \
    UPLOAD_DIR=/data/uploads
COPY backend/requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt \
    && useradd --create-home app \
    && mkdir -p /data/uploads \
    && chown -R app:app /data
COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/migrations ./migrations
COPY --chown=app:app backend/alembic.ini backend/start.py backend/cloud_start.py ./
COPY --from=frontend --chown=app:app /build/dist ./static
EXPOSE 8000
# The bootstrap gives the mounted uploads directory to app, then drops root.
CMD ["python", "cloud_start.py"]
