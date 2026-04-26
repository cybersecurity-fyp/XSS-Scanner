"""
tests/test_dependencies.py — Unit tests for app/dependencies.py.

Tests validate_safe_url (SSRF protection), require_auth, and require_admin
using real FastAPI request objects via TestClient.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient
from fastapi import FastAPI
from tests.conftest import TEST_USER, TEST_ADMIN, make_session_cookie


# ─────────────────────────────────────────────────────────────────────────────
#  validate_safe_url — pure function tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def validate_url():
    from app.dependencies import validate_safe_url
    return validate_safe_url


class TestValidateSafeUrl:
    def test_valid_https_url_returns_url(self, validate_url):
        result = validate_url('https://example.com/page?q=test')
        assert result == 'https://example.com/page?q=test'

    def test_valid_http_url_returns_url(self, validate_url):
        result = validate_url('http://example.com')
        assert result == 'http://example.com'

    def test_ftp_scheme_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            validate_url('ftp://example.com')
        assert exc.value.status_code == 400

    def test_no_scheme_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('example.com')

    def test_localhost_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            validate_url('http://localhost/admin')
        assert exc.value.status_code == 400

    def test_127_0_0_1_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://127.0.0.1/')

    def test_private_ip_192_168_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://192.168.1.100/')

    def test_private_ip_10_0_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://10.0.0.1/')

    def test_private_ip_172_16_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://172.16.0.1/')

    def test_link_local_169_254_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://169.254.169.254/latest/meta-data')

    def test_aws_metadata_domain_raises_400(self, validate_url):
        """AWS metadata IP should be blocked."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://169.254.169.254/')

    def test_gcp_metadata_domain_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://metadata.google.internal/')

    def test_azure_metadata_domain_raises_400(self, validate_url):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_url('http://168.63.129.16/')

    def test_hostname_is_not_blocked(self, validate_url):
        """Public hostnames should pass through even if they could resolve privately."""
        result = validate_url('https://public-site.example.com/')
        assert 'public-site.example.com' in result

    def test_url_with_query_string_passes(self, validate_url):
        url = 'https://example.com/search?q=xss&page=1'
        assert validate_url(url) == url

    def test_url_with_fragment_passes(self, validate_url):
        url = 'https://example.com/page#section'
        assert validate_url(url) == url


# ─────────────────────────────────────────────────────────────────────────────
#  require_auth / require_admin — via lightweight test app
# ─────────────────────────────────────────────────────────────────────────────
#  We create a tiny FastAPI app that exposes /auth-test and /admin-test routes,
#  then use TestClient to exercise the session-based auth checks.

@pytest.fixture(scope='module')
def mini_client(patch_db):
    """Tiny app with two routes to test auth dependencies."""
    from starlette.middleware.sessions import SessionMiddleware
    from app.dependencies import require_auth, require_admin
    from app.config import settings

    mini = FastAPI()
    mini.add_middleware(SessionMiddleware,
                        secret_key=settings.session_secret,
                        session_cookie='xssniper_session',
                        max_age=86400)

    @mini.get('/auth-test')
    def auth_test(request: Request):
        user = require_auth(request)
        return {'id': user['id']}

    @mini.get('/admin-test')
    def admin_test(request: Request):
        user = require_admin(request)
        return {'role': user['role']}

    with TestClient(mini, raise_server_exceptions=True) as c:
        yield c


class TestRequireAuth:
    def test_no_session_returns_401(self, mini_client):
        r = mini_client.get('/auth-test')
        assert r.status_code == 401

    def test_authenticated_user_returns_200(self, mini_client):
        cookies = {'xssniper_session': make_session_cookie({'user': TEST_USER})}
        r = mini_client.get('/auth-test', cookies=cookies)
        assert r.status_code == 200
        assert r.json()['id'] == TEST_USER['id']


class TestRequireAdmin:
    def test_no_session_returns_401(self, mini_client):
        r = mini_client.get('/admin-test')
        assert r.status_code == 401

    def test_regular_user_returns_403(self, mini_client):
        cookies = {'xssniper_session': make_session_cookie({'user': TEST_USER})}
        r = mini_client.get('/admin-test', cookies=cookies)
        assert r.status_code == 403

    def test_admin_user_returns_200(self, mini_client):
        cookies = {'xssniper_session': make_session_cookie({'user': TEST_ADMIN})}
        r = mini_client.get('/admin-test', cookies=cookies)
        assert r.status_code == 200
        assert r.json()['role'] == 'admin'
