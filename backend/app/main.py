import asyncio
import os
import mimetypes
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from . import auth, menu, orders, analytics
from .db import SessionLocal
from .realtime import hub
from .config import allowed_origins
from .frontend import FrontendFiles

app = FastAPI(title='StreetSide Operations API', version='1.0.0')
origins = allowed_origins()


@app.middleware('http')
async def secure_requests(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if (origin and origin not in origins) or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Request origin is not allowed'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


app.include_router(auth.router)
app.include_router(menu.router)
app.include_router(menu.admin)
app.include_router(orders.router)
app.include_router(analytics.router)
mimetypes.add_type('image/webp', '.webp')
app.mount('/uploads', StaticFiles(directory=menu.UPLOAD_DIR), name='uploads')


@app.get('/api/health')
def health():
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ok'}


@app.websocket('/api/ws')
async def websocket(ws: WebSocket):
    if ws.headers.get('origin') not in origins:
        await ws.close(code=1008)
        return
    def authenticated():
        with SessionLocal() as db:
            return auth.session_user(ws.cookies.get(auth.COOKIE), db) is not None
    if not authenticated():
        await ws.close(code=1008)
        return
    await ws.accept()
    hub.clients.add(ws)
    try:
        await ws.send_json({'type': 'connected'})
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=25)
            except asyncio.TimeoutError:
                pass
            if not authenticated():
                await ws.close(code=1008)
                break
            await ws.send_json({'type': 'heartbeat'})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        hub.clients.discard(ws)


# Registered last so API, WebSocket and uploaded-image routes keep priority.
if os.getenv('FRONTEND_DIST'):
    app.mount('/', FrontendFiles(directory=os.environ['FRONTEND_DIST']), name='frontend')
