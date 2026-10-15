FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --create-home app && mkdir -p /data/uploads && chown -R app:app /data
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["python", "start.py"]
