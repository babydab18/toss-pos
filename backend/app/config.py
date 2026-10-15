"""Environment settings shared by local, Compose and hosted deployments."""
import os


def normalize_database_url(value: str) -> str:
    # Managed hosts supply plain postgres URLs; this project uses psycopg 3.
    for prefix in ('postgres://', 'postgresql://'):
        if value.startswith(prefix):
            return 'postgresql+psycopg://' + value[len(prefix):]
    return value


def allowed_origins() -> set[str]:
    public_url = os.getenv('RENDER_EXTERNAL_URL', '').rstrip('/')
    defaults = '' if public_url else 'http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080'
    origins = {s.strip().rstrip('/') for s in os.getenv('ALLOWED_ORIGINS', defaults).split(',') if s.strip()}
    if public_url:
        origins.add(public_url)
    return origins
