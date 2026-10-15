from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Mount
from app.config import allowed_origins, normalize_database_url
from app.frontend import FrontendFiles


def test_managed_database_urls_preserve_credentials():
    suffix = 'staff:p%40ss%3Aword@db.internal:5432/toss?sslmode=require'
    for scheme in ('postgres://', 'postgresql://', 'postgresql+psycopg://'):
        assert normalize_database_url(scheme + suffix) == 'postgresql+psycopg://' + suffix
    assert normalize_database_url('sqlite:///test.db') == 'sqlite:///test.db'


def test_render_origin_and_custom_domain(monkeypatch):
    monkeypatch.delenv('ALLOWED_ORIGINS', raising=False)
    monkeypatch.setenv('RENDER_EXTERNAL_URL', 'https://toss-example.onrender.com/')
    assert allowed_origins() == {'https://toss-example.onrender.com'}
    monkeypatch.setenv('ALLOWED_ORIGINS', 'https://orders.example.com/, https://toss.example.com')
    assert allowed_origins() == {
        'https://toss-example.onrender.com', 'https://orders.example.com', 'https://toss.example.com'
    }


def test_hosted_ui_routes_assets_and_private_files(tmp_path):
    (tmp_path / 'index.html').write_text('<html>TOSS</html>')
    (tmp_path / '.env').write_text('must-not-be-served')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets/app-hash.js').write_text('window.TOSS = true;')
    app = Starlette(routes=[Mount('/', FrontendFiles(directory=tmp_path))])
    with TestClient(app) as client:
        for route in ('/', '/kitchen', '/orders', '/admin', '/analytics'):
            response = client.get(route)
            assert response.status_code == 200
            assert response.text == '<html>TOSS</html>'
            assert response.headers['cache-control'] == 'no-cache'
            assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        response = client.get('/assets/app-hash.js')
        assert response.status_code == 200
        assert 'immutable' in response.headers['cache-control']
        for route in ('/.env', '/assets/missing.js', '/api/missing', '/%2e%2e/start.py'):
            assert client.get(route).status_code == 404


def test_https_cookie_and_origin_protection(client, monkeypatch):
    from app.main import origins
    monkeypatch.setenv('COOKIE_SECURE', 'true')
    monkeypatch.setattr('app.main.origins', origins | {'https://toss-example.onrender.com'})
    response = client.post('/api/auth/login',
        json={'username': 'admin', 'password': 'test-only-password-123'},
        headers={'origin': 'https://toss-example.onrender.com'})
    assert response.status_code == 200
    cookie = response.headers['set-cookie'].lower()
    assert 'secure' in cookie and 'httponly' in cookie and 'samesite=strict' in cookie
    assert client.post('/api/auth/login',
        json={'username': 'admin', 'password': 'test-only-password-123'},
        headers={'origin': 'https://untrusted.example'}).status_code == 403
