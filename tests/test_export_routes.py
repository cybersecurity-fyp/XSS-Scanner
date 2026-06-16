"""
tests/test_export_routes.py — Integration tests for history, stats and export
endpoints (/api/v1/stats, /api/v1/history, /api/v1/csv, /api/v1/json, /api/v1/pdf).
"""

import pytest
from unittest.mock import patch
from tests.conftest import TEST_USER, TEST_ADMIN

SAMPLE_SCAN = {
    'id':              1,
    'user_id':         TEST_USER['id'],
    'date':            '2026-03-19T10:00:00+00:00',
    'url':             'https://example.com',
    'status':          'Completed',
    'vulnerabilities': 2,
    'log_output':      '[+] XSS VULNERABLE found\n[+] XSS VULNERABLE found',
    'config':          {},
    'duration':        3.14,
}

OTHER_SCAN = {**SAMPLE_SCAN, 'id': 2, 'user_id': 999}  # owned by another user


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/stats
# ─────────────────────────────────────────────────────────────────────────────

class TestStatsRoute:
    URL = '/api/v1/stats'

    def test_unauthenticated_returns_401(self, client):
        r = client.get(self.URL)
        assert r.status_code == 401

    def test_returns_stats_dict(self, client, auth_cookies):
        stats = {'total': 5, 'vulns': 3, 'health': 100.0}
        with patch('app.routers.export.get_stats', return_value=stats):
            r = client.get(self.URL, cookies=auth_cookies)
        assert r.status_code == 200
        data = r.json()
        assert data['total'] == 5
        assert data['vulns'] == 3
        assert 'health' in data

    def test_stats_filters_by_current_user(self, client, auth_cookies):
        """get_stats must be called with the authenticated user's id."""
        stats = {'total': 0, 'vulns': 0, 'health': 100.0}
        with patch('app.routers.export.get_stats', return_value=stats) as mock_stats:
            client.get(self.URL, cookies=auth_cookies)
        mock_stats.assert_called_once_with(user_id=TEST_USER['id'])


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/history
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryRoute:
    URL = '/api/v1/history'

    def test_unauthenticated_returns_401(self, client):
        r = client.get(self.URL)
        assert r.status_code == 401

    def test_returns_list(self, client, auth_cookies):
        with patch('app.routers.export.get_history', return_value=[SAMPLE_SCAN]):
            r = client.get(self.URL, cookies=auth_cookies)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_history_filters_by_current_user(self, client, auth_cookies):
        with patch('app.routers.export.get_history', return_value=[]) as mock_hist:
            client.get(self.URL, cookies=auth_cookies)
        mock_hist.assert_called_once_with(user_id=TEST_USER['id'])


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/history/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestScanDetailRoute:
    def test_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/history/1')
        assert r.status_code == 401

    def test_scan_not_found_returns_404(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=None):
            r = client.get('/api/v1/history/999', cookies=auth_cookies)
        assert r.status_code == 404

    def test_own_scan_returns_200(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN):
            r = client.get('/api/v1/history/1', cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['id'] == 1

    def test_other_users_scan_returns_403(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=OTHER_SCAN):
            r = client.get('/api/v1/history/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_admin_can_access_any_scan(self, client, admin_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=OTHER_SCAN):
            r = client.get('/api/v1/history/2', cookies=admin_cookies)
        assert r.status_code == 200

    def test_legacy_scan_no_user_id_accessible(self, client, auth_cookies):
        """Scans without user_id (legacy) must be accessible for backwards compat."""
        legacy_scan = {**SAMPLE_SCAN, 'user_id': None}
        with patch('app.routers.export.get_scan_detail', return_value=legacy_scan):
            r = client.get('/api/v1/history/1', cookies=auth_cookies)
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /api/v1/history/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteScanRoute:
    def test_unauthenticated_returns_401(self, client):
        r = client.delete('/api/v1/history/1')
        assert r.status_code == 401

    def test_delete_not_found_returns_404(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=None):
            r = client.delete('/api/v1/history/999', cookies=auth_cookies)
        assert r.status_code == 404

    def test_delete_other_users_scan_returns_403(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=OTHER_SCAN):
            r = client.delete('/api/v1/history/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_delete_own_scan_returns_success(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN), \
             patch('app.db.scans.delete_scan', return_value=True):
            r = client.delete('/api/v1/history/1', cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/csv/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestExportCSV:
    def test_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/csv/1')
        assert r.status_code == 401

    def test_csv_not_found_returns_404(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=None):
            r = client.get('/api/v1/csv/999', cookies=auth_cookies)
        assert r.status_code == 404

    def test_csv_own_scan_returns_csv(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN):
            r = client.get('/api/v1/csv/1', cookies=auth_cookies)
        assert r.status_code == 200
        assert 'text/csv' in r.headers['content-type']
        assert b'Vulnerabilities' in r.content

    def test_csv_other_users_scan_returns_403(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=OTHER_SCAN):
            r = client.get('/api/v1/csv/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_csv_filename_includes_scan_id(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN):
            r = client.get('/api/v1/csv/1', cookies=auth_cookies)
        assert 'scan_1.csv' in r.headers.get('content-disposition', '')


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/json/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestExportJSON:
    def test_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/json/1')
        assert r.status_code == 401

    def test_json_own_scan_returns_json(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN):
            r = client.get('/api/v1/json/1', cookies=auth_cookies)
        assert r.status_code == 200
        assert 'application/json' in r.headers['content-type']

    def test_json_other_users_scan_returns_403(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=OTHER_SCAN):
            r = client.get('/api/v1/json/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_json_content_has_expected_fields(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN):
            r = client.get('/api/v1/json/1', cookies=auth_cookies)
        data = r.json()
        for field in ('scan_id', 'date', 'url', 'status', 'vulnerabilities', 'duration'):
            assert field in data


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/pdf/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestExportPDF:
    def test_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/pdf/1')
        assert r.status_code == 401

    def test_pdf_not_found_returns_404(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=None):
            r = client.get('/api/v1/pdf/999', cookies=auth_cookies)
        assert r.status_code == 404

    def test_pdf_other_users_scan_returns_403(self, client, auth_cookies):
        with patch('app.routers.export.get_scan_detail', return_value=OTHER_SCAN):
            r = client.get('/api/v1/pdf/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_pdf_own_scan_returns_pdf(self, client, auth_cookies):
        """Only runs if reportlab is installed; skips gracefully if not."""
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip('reportlab not installed')
        with patch('app.routers.export.get_scan_detail', return_value=SAMPLE_SCAN):
            r = client.get('/api/v1/pdf/1', cookies=auth_cookies)
        assert r.status_code == 200
        assert r.content[:4] == b'%PDF'
