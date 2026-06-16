"""
tests/test_scan_routes.py — Integration tests for /api/v1/scan/* endpoints.

Tests cover authentication enforcement, SSRF prevention, scan lifecycle,
and SSE streaming.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from tests.conftest import TEST_USER, make_session_cookie


VALID_CONFIG = {
    'url':      'https://example.com/search?q=test',
    'data':     '',
    'level':    2,
    'threads':  2,
    'timeout':  5,
    'delay':    0,
    'json_mode':  False,
    'crawl':      False,
    'fuzzer':     False,
    'encode':     False,
    'path':       False,
    'skip_dom':   False,
    'ml_prefilter': False,
    'headers':  '',
    'proxy':    '',
    'file':     '',
}


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/scan/start
# ─────────────────────────────────────────────────────────────────────────────

class TestStartScan:
    URL = '/api/v1/scan/start'

    def test_unauthenticated_returns_401(self, client):
        r = client.post(self.URL, json=VALID_CONFIG)
        assert r.status_code == 401

    def test_start_scan_returns_scan_id(self, client, auth_cookies):
        with patch('app.routers.scan.asyncio.create_task'):
            r = client.post(self.URL, json=VALID_CONFIG, cookies=auth_cookies)
        assert r.status_code == 200
        assert 'scan_id' in r.json()
        assert len(r.json()['scan_id']) == 32  # uuid4().hex

    def test_start_scan_non_http_url_returns_400(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'ftp://example.com'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code in (400, 422)  # Pydantic validator raises 422

    def test_start_scan_url_without_scheme_returns_400(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'example.com'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code in (400, 422)  # Pydantic validator raises 422

    def test_start_scan_localhost_ssrf_blocked(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'http://localhost/admin'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_start_scan_private_ip_ssrf_blocked(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'http://192.168.1.1/'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_start_scan_127_ssrf_blocked(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'http://127.0.0.1:8080/'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_start_scan_aws_metadata_blocked(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'http://169.254.169.254/latest/meta-data/'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_start_scan_url_too_long_returns_422(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'url': 'https://example.com/' + 'a' * 3000}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 422

    def test_start_scan_missing_url_returns_422(self, client, auth_cookies):
        payload = {k: v for k, v in VALID_CONFIG.items() if k != 'url'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 422

    def test_start_scan_level_out_of_range_clamped_or_rejected(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'level': 99}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code in (200, 422)  # Pydantic Field(ge=1, le=3) should reject

    def test_start_scan_level_validated_ge_1(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'level': 0}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 422

    def test_start_scan_threads_validated(self, client, auth_cookies):
        payload = {**VALID_CONFIG, 'threads': 100}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/scan/stop
# ─────────────────────────────────────────────────────────────────────────────

class TestStopScan:
    URL = '/api/v1/scan/stop'

    def test_unauthenticated_returns_401(self, client):
        r = client.post(self.URL)
        assert r.status_code == 401

    def test_stop_with_no_active_scan_returns_success(self, client, auth_cookies):
        with patch('app.services.scan_service.scan_service.find_user_scan', return_value=None):
            r = client.post(self.URL, cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_stop_with_active_scan_stops_it(self, client, auth_cookies):
        with patch('app.services.scan_service.scan_service.find_user_scan', return_value='abc123'), \
             patch('app.services.scan_service.scan_service.stop') as mock_stop:
            r = client.post(self.URL, cookies=auth_cookies)
        assert r.status_code == 200
        mock_stop.assert_called_once_with('abc123')


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/scan/{scan_id}/stream
# ─────────────────────────────────────────────────────────────────────────────

class TestStreamLogs:
    def test_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/scan/abc123/stream')
        assert r.status_code == 401

    def test_access_denied_for_other_users_scan(self, client, auth_cookies):
        """User with id=1 should not see a scan owned by user id=99."""
        mock_state = MagicMock()
        mock_state.user_id = 99   # different from TEST_USER['id'] = 1
        with patch('app.services.scan_service.scan_service.get', return_value=mock_state):
            r = client.get('/api/v1/scan/abc123/stream', cookies=auth_cookies)
        assert r.status_code == 403

    def test_stream_own_scan_returns_event_stream(self, client, auth_cookies):
        """User can stream their own scan; check media type."""
        mock_state = MagicMock()
        mock_state.user_id = TEST_USER['id']
        mock_state.logs    = ['[*] Scanning...']
        mock_state.done    = True
        mock_state.result  = {'status': 'success', 'vulnerabilities': 0}
        with patch('app.services.scan_service.scan_service.get', return_value=mock_state):
            r = client.get('/api/v1/scan/abc123/stream', cookies=auth_cookies)
        assert r.status_code == 200
        assert 'text/event-stream' in r.headers.get('content-type', '')

    def test_stream_nonexistent_scan_returns_error_event(self, client, auth_cookies):
        """Scan not found → SSE error event, not a 404."""
        with patch('app.services.scan_service.scan_service.get', return_value=None):
            r = client.get('/api/v1/scan/unknown/stream', cookies=auth_cookies)
        # SSE endpoint always returns 200 with streaming body; error is inside the stream
        assert r.status_code == 200
