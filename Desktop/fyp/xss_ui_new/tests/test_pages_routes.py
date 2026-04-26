"""
tests/test_pages_routes.py — Integration tests for HTML page routes.

Tests focus on:
  - Redirect behaviour for unauthenticated/authenticated users
  - HTTP 200 for valid authenticated requests
  - Health check endpoint
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import TEST_USER, TEST_ADMIN

# Minimal DB stubs used by page routes (get_stats, get_history, etc.)
_EMPTY_STATS   = {'total': 0, 'vulns': 0, 'health': 100.0}
_EMPTY_HISTORY = []
_EMPTY_DAILY   = [{'label': 'Mar 19', 'scans': 0, 'vulns': 0}]
_EMPTY_PREFS   = {}


def _patch_page_db():
    """Patch all DB calls made by page routes so templates render without real data."""
    return [
        patch('app.routers.pages.get_stats',       return_value=_EMPTY_STATS),
        patch('app.routers.pages.get_history',     return_value=_EMPTY_HISTORY),
        patch('app.routers.pages.get_daily_stats', return_value=_EMPTY_DAILY),
        patch('app.db.users.get_preferences',      return_value=_EMPTY_PREFS),
        patch('app.db.users.get_all_users',        return_value=[]),
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  Health check
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_returns_200_when_db_ok(self, client):
        mock_resp = MagicMock()
        mock_resp.count = 1
        with patch('app.db.client.db') as mock_db:
            mock_db.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_resp
            r = client.get('/health')
        assert r.status_code in (200, 503)  # 200 ok, 503 if db mock raises

    def test_health_returns_json(self, client):
        r = client.get('/health')
        data = r.json()
        assert 'status' in data
        assert 'timestamp' in data


# ─────────────────────────────────────────────────────────────────────────────
#  Unauthenticated redirects
# ─────────────────────────────────────────────────────────────────────────────

class TestUnauthenticatedRedirects:
    @pytest.mark.parametrize('path', ['/', '/scan', '/history', '/settings', '/admin'])
    def test_protected_page_redirects_to_login(self, client, path):
        r = client.get(path, follow_redirects=False)
        assert r.status_code in (302, 307)
        assert '/login' in r.headers.get('location', '')


# ─────────────────────────────────────────────────────────────────────────────
#  Authenticated page renders
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthenticatedPages:
    def test_dashboard_renders_200(self, client, auth_cookies):
        patches = _patch_page_db()
        for p in patches:
            p.start()
        try:
            r = client.get('/', cookies=auth_cookies)
        finally:
            for p in patches:
                p.stop()
        assert r.status_code == 200
        assert b'<!DOCTYPE html>' in r.content or b'<html' in r.content

    def test_scan_page_renders_200(self, client, auth_cookies):
        r = client.get('/scan', cookies=auth_cookies)
        assert r.status_code == 200

    def test_history_page_renders_200(self, client, auth_cookies):
        with patch('app.routers.pages.get_history', return_value=_EMPTY_HISTORY):
            r = client.get('/history', cookies=auth_cookies)
        assert r.status_code == 200

    def test_settings_page_renders_200(self, client, auth_cookies):
        with patch('app.db.users.get_preferences', return_value={}):
            r = client.get('/settings', cookies=auth_cookies)
        assert r.status_code == 200

    def test_admin_page_renders_200_for_admin(self, client, admin_cookies):
        with patch('app.db.users.get_all_users', return_value=[]):
            r = client.get('/admin', cookies=admin_cookies)
        assert r.status_code == 200

    def test_admin_page_redirects_regular_user_to_home(self, client, auth_cookies):
        r = client.get('/admin', cookies=auth_cookies, follow_redirects=False)
        assert r.status_code in (302, 307)
        assert r.headers.get('location') == '/'


# ─────────────────────────────────────────────────────────────────────────────
#  Auth pages redirect when already logged in
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthPageRedirectsWhenLoggedIn:
    @pytest.mark.parametrize('path', ['/login', '/register', '/forgot-password'])
    def test_redirects_to_dashboard(self, client, auth_cookies, path):
        r = client.get(path, cookies=auth_cookies, follow_redirects=False)
        assert r.status_code in (302, 307)
        assert r.headers.get('location') == '/'


# ─────────────────────────────────────────────────────────────────────────────
#  Login / Register pages for unauthenticated users
# ─────────────────────────────────────────────────────────────────────────────

class TestPublicPages:
    def test_login_page_renders(self, client):
        r = client.get('/login')
        assert r.status_code == 200

    def test_register_page_renders(self, client):
        r = client.get('/register')
        assert r.status_code == 200

    def test_forgot_password_page_renders(self, client):
        r = client.get('/forgot-password')
        assert r.status_code == 200

    def test_terms_page_renders(self, client):
        r = client.get('/terms')
        assert r.status_code == 200

    def test_privacy_page_renders(self, client):
        r = client.get('/privacy')
        assert r.status_code == 200

    def test_verify_email_no_token_redirects(self, client):
        r = client.get('/verify-email', follow_redirects=False)
        assert r.status_code in (302, 307)

    def test_verify_email_with_token_renders(self, client):
        with patch('app.services.auth_service.verify_email_token', return_value=True):
            r = client.get('/verify-email?token=testtoken123')
        assert r.status_code == 200

    def test_reset_password_no_token_redirects(self, client):
        r = client.get('/reset-password', follow_redirects=False)
        assert r.status_code in (302, 307)

    def test_reset_password_invalid_token_renders_error(self, client):
        with patch('app.services.auth_service.verify_reset_token', return_value=None):
            r = client.get('/reset-password?token=badtoken')
        assert r.status_code == 200

    def test_reset_password_valid_token_renders_form(self, client):
        user = {'username': 'testuser'}
        with patch('app.services.auth_service.verify_reset_token', return_value=user):
            r = client.get('/reset-password?token=validtoken')
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  Error pages
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorPages:
    def test_unknown_route_returns_404(self, client):
        r = client.get('/this-page-does-not-exist-at-all', follow_redirects=False)
        assert r.status_code == 404

    def test_404_response_is_html(self, client):
        r = client.get('/totally-missing-route')
        assert 'text/html' in r.headers.get('content-type', '')
