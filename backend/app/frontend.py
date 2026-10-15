"""Serve the compiled UI when running the single-container deployment."""
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace('\\', '/')
        # Only actual client routes fall back to the SPA. Missing API endpoints
        # and missing assets must remain 404s rather than returning HTML.
        if path.strip('/') in ('', '.', 'kitchen', 'orders', 'admin', 'analytics'):
            path = 'index.html'
        if any(part.startswith('.') for part in path.split('/')):
            raise HTTPException(status_code=404)
        response = await super().get_response(path, scope)
        response.headers['Cache-Control'] = (
            'public, max-age=31536000, immutable' if path.startswith('assets/')
            else 'no-cache'
        )
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self' ws: wss:; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'"
        )
        return response
