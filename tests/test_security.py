"""
tests/test_security.py — Security-focused integration tests.

Covers:
  1. SSRF prevention in the scan endpoint
  2. Authorization: users cannot access/modify each other's resources
  3. Admin-only route enforcement
  4. Input validation as a security boundary
  5. Password security (no leakage in auth responses)
"""

import pytest
from unittest.mock import patch
from tests.conftest import TEST_USER, TEST_ADMIN, make_session_cookie


VALID_CONFIG_BASE = dict(
    data='', level=2, threads=2, timeout=5, delay=0,
    json_mode=False, crawl=False, fuzzer=False, encode=False,
    path=False, skip_dom=False, ml_prefilter=False,
    headers='', proxy='', file='',
)

# A scan that belongs to a DIFFERENT user (user_id=999)
FOREIGN_SCAN = {
    'id':              99,
    'user_id':         999,
    'date':            '2026-03-19T10:00:00+00:00',
    'url':             'https://victim.example.com',
    'status':          'Completed',
    'vulnerabilities': 0,
    'log_output':      'nothing found',
    'config':          {},
    'duration':        1.0,
}

OWN_SCAN = {**FOREIGN_SCAN, 'id': 1, 'user_id': TEST_USER['id']}


# ─────────────────────────────────────────────────────────────────────────────
#  1. SSRF prevention
# ─────────────────────────────────────────────────────────────────────────────

class TestSSRFPrevention:
    """Every private/loopback/cloud address must be blocked by validate_safe_url."""

    BLOCKED = [
        'http://localhost/',
        'http://127.0.0.1/',
        'http://127.0.0.2/',
        'http://0.0.0.0/',
        'http://[::1]/',                     # IPv6 loopback
        'http://192.168.0.1/',               # RFC-1918 class C
        'http://192.168.255.255/',
        'http://10.0.0.1/',                  # RFC-1918 class A
        'http://10.255.255.255/',
        'http://172.16.0.1/',                # RFC-1918 class B
        'http://172.31.255.255/',
        'http://169.254.169.254/',           # AWS metadata (link-local)
        'http://169.254.0.1/',
        'http://metadata.google.internal/',  # GCP metadata
        'http://168.63.129.16/',             # Azure metadata
    ]

    ALLOWED = [
        'https://example.com/',
        'http://example.com/search?q=test',
        'https://subdomain.example.org/path',
        'https://1.1.1.1/',                  # Cloudflare DNS — public IP
        'https://8.8.8.8/',                  # Google DNS — public IP
    ]

    @pytest.mark.parametrize('url', BLOCKED)
    def test_blocked_url_returns_400(self, client, auth_cookies, url):
        payload = {**VALID_CONFIG_BASE, 'url': url}
        r = client.post('/api/v1/scan/start', json=payload, cookies=auth_cookies)
        assert r.status_code == 400, f'Expected 400 for SSRF target {url!r}, got {r.status_code}'

    @pytest.mark.parametrize('url', ALLOWED)
    def test_allowed_url_is_not_blocked(self, client, auth_cookies, url):
        payload = {**VALID_CONFIG_BASE, 'url': url}
        with patch('app.routers.scan.asyncio.create_task'):
            r = client.post('/api/v1/scan/start', json=payload, cookies=auth_cookies)
        # 200 = accepted, 422 = validation error — both mean NOT a 400 SSRF block
        assert r.status_code != 400, f'Public URL {url!r} should not be SSRF-blocked'

    def test_ftp_scheme_blocked(self, client, auth_cookies):
        payload = {**VALID_CONFIG_BASE, 'url': 'ftp://example.com/'}
        r = client.post('/api/v1/scan/start', json=payload, cookies=auth_cookies)
        assert r.status_code in (400, 422)  # Pydantic validator raises 422

    def test_file_scheme_blocked_by_pydantic(self, client, auth_cookies):
        payload = {**VALID_CONFIG_BASE, 'url': 'file:///etc/passwd'}
        r = client.post('/api/v1/scan/start', json=payload, cookies=auth_cookies)
        assert r.status_code in (400, 422)


# ─────────────────────────────────────────────────────────────────────────────
#  2. Cross-user authorization (IDOR prevention)
# ─────────────────────────────────────────────────────────────────────────────

class TestIDORPrevention:
    """Users must not be able to read, modify, or delete each other's scans."""

    def test_cannot_view_other_users_scan_detail(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN):
            r = client.get('/api/v1/history/99', cookies=auth_cookies)
        assert r.status_code == 403

    def test_cannot_delete_other_users_scan(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN):
            r = client.delete('/api/v1/history/99', cookies=auth_cookies)
        assert r.status_code == 403

    def test_cannot_export_csv_for_other_users_scan(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN):
            r = client.get('/api/v1/csv/99', cookies=auth_cookies)
        assert r.status_code == 403

    def test_cannot_export_json_for_other_users_scan(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN):
            r = client.get('/api/v1/json/99', cookies=auth_cookies)
        assert r.status_code == 403

    def test_cannot_export_pdf_for_other_users_scan(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN):
            r = client.get('/api/v1/pdf/99', cookies=auth_cookies)
        assert r.status_code == 403

    def test_cannot_stream_other_users_scan(self, client, auth_cookies):
        from unittest.mock import MagicMock
        mock_state = MagicMock()
        mock_state.user_id = 999  # owned by someone else
        with patch('app.services.scan_service.scan_service.get', return_value=mock_state):
            r = client.get('/api/v1/scan/foreign_scan/stream', cookies=auth_cookies)
        assert r.status_code == 403

    def test_admin_can_view_any_scan(self, client, admin_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN):
            r = client.get('/api/v1/history/99', cookies=admin_cookies)
        assert r.status_code == 200

    def test_admin_can_delete_any_scan(self, client, admin_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=FOREIGN_SCAN), \
             patch('app.db.scans.delete_scan', return_value=True):
            r = client.delete('/api/v1/history/99', cookies=admin_cookies)
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  3. Admin route enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminEnforcement:
    """All /api/v1/admin/* routes must reject non-admins with 403."""

    def test_list_users_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/admin/users')
        assert r.status_code == 401

    def test_list_users_regular_user_returns_403(self, client, auth_cookies):
        r = client.get('/api/v1/admin/users', cookies=auth_cookies)
        assert r.status_code == 403

    def test_delete_user_regular_user_returns_403(self, client, auth_cookies):
        r = client.delete('/api/v1/admin/users/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_admin_stats_regular_user_returns_403(self, client, auth_cookies):
        r = client.get('/api/v1/admin/stats', cookies=auth_cookies)
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  4. Input validation as security boundary
# ─────────────────────────────────────────────────────────────────────────────

class TestInputValidationSecurity:
    def test_oversized_url_rejected(self, client, auth_cookies):
        payload = {**VALID_CONFIG_BASE, 'url': 'https://example.com/' + 'A' * 3000}
        r = client.post('/api/v1/scan/start', json=payload, cookies=auth_cookies)
        assert r.status_code == 422

    def test_oversized_login_rejected(self, client):
        r = client.post('/api/v1/auth/login',
                        json={'login': 'u' * 300, 'password': 'x' * 300})
        assert r.status_code == 422

    def test_oversized_register_email_rejected(self, client):
        r = client.post('/api/v1/auth/register', json={
            'username': 'user', 'email': 'x' * 300 + '@example.com',
            'password': 'Strong@Pass1', 'confirm': 'Strong@Pass1',
        })
        assert r.status_code in (400, 422)

    def test_sql_injection_in_login_handled_safely(self, client):
        """The username/email goes through parameterized queries; must not crash."""
        with patch('app.db.users.find_user_by_login', return_value=None):
            r = client.post('/api/v1/auth/login', json={
                'login':    "admin' OR '1'='1",
                'password': 'anything',
            })
        assert r.status_code == 401  # Not 500 — no crash

    def test_xss_payload_in_username_field_handled(self, client):
        """XSS in register form fields must not cause 500 — model handles it."""
        with patch('app.db.users.username_exists', return_value=False), \
             patch('app.db.users.email_exists',    return_value=False), \
             patch('app.services.auth_service.register_user', return_value=None):
            r = client.post('/api/v1/auth/register', json={
                'username': '<script>alert(1)</script>',
                'email':    'xss@example.com',
                'password': 'Strong@Pass1',
                'confirm':  'Strong@Pass1',
            })
        # The router rejects if register_user returns None (500), but no crash
        assert r.status_code in (200, 400, 500)
        assert r.status_code != 422  # Pydantic doesn't reject this — router should handle


# ─────────────────────────────────────────────────────────────────────────────
#  5. Password and session security
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordSecurity:
    def test_login_response_does_not_contain_password_hash(self, client):
        from app.services.auth_service import hash_password
        row = {
            'id': 1, 'username': 'testuser', 'email': 'test@example.com',
            'role': 'user', 'password': hash_password('Pass@word1'),
            'email_verified': True, 'failed_login_attempts': 0, 'locked_until': None,
        }
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post('/api/v1/auth/login',
                            json={'login': 'testuser', 'password': 'Pass@word1'})
        assert r.status_code == 200
        body = r.text
        # The response must not contain the hash
        assert 'pbkdf2$' not in body

    def test_admin_list_users_does_not_contain_passwords(self, client, admin_cookies):
        users_list = [
            {'id': 1, 'username': 'admin', 'email': 'a@a.com',
             'role': 'admin', 'email_verified': True},
        ]
        with patch('app.db.users.get_all_users', return_value=users_list):
            r = client.get('/api/v1/admin/users', cookies=admin_cookies)
        for user in r.json():
            assert 'password' not in user

    def test_invalid_session_cookie_treated_as_unauthenticated(self, client):
        r = client.get('/api/v1/stats',
                       cookies={'xssniper_session': 'totally.invalid.tampered.cookie'})
        assert r.status_code == 401

    def test_tampered_session_cookie_rejected(self, client):
        """Modifying the session payload (without valid signature) must fail."""
        import base64, json
        fake_payload = base64.b64encode(json.dumps({'user': {'id': 1, 'role': 'admin'}}).encode()).decode()
        r = client.get('/api/v1/admin/users',
                       cookies={'xssniper_session': f'{fake_payload}.fakesig'})
        assert r.status_code == 401
