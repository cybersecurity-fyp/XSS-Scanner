"""
tests/test_admin_routes.py — Integration tests for /api/v1/admin/* endpoints.
"""

import pytest
from unittest.mock import patch
from tests.conftest import TEST_USER, TEST_ADMIN


SAMPLE_USERS = [
    {'id': 1, 'username': 'admin',    'email': 'admin@example.com',   'role': 'admin',  'email_verified': True},
    {'id': 2, 'username': 'testuser', 'email': 'testuser@example.com', 'role': 'user',   'email_verified': True},
    {'id': 3, 'username': 'other',    'email': 'other@example.com',    'role': 'user',   'email_verified': False},
]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/admin/users
# ─────────────────────────────────────────────────────────────────────────────

class TestListUsers:
    URL = '/api/v1/admin/users'

    def test_unauthenticated_returns_401(self, client):
        r = client.get(self.URL)
        assert r.status_code == 401

    def test_regular_user_returns_403(self, client, auth_cookies):
        r = client.get(self.URL, cookies=auth_cookies)
        assert r.status_code == 403

    def test_admin_returns_user_list(self, client, admin_cookies):
        with patch('app.routers.admin.get_all_users', return_value=SAMPLE_USERS):
            r = client.get(self.URL, cookies=admin_cookies)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert len(users) == 3

    def test_admin_response_has_expected_fields(self, client, admin_cookies):
        with patch('app.routers.admin.get_all_users', return_value=SAMPLE_USERS):
            r = client.get(self.URL, cookies=admin_cookies)
        user = r.json()[0]
        for field in ('id', 'username', 'email', 'role', 'email_verified'):
            assert field in user

    def test_response_does_not_contain_passwords(self, client, admin_cookies):
        with patch('app.routers.admin.get_all_users', return_value=SAMPLE_USERS):
            r = client.get(self.URL, cookies=admin_cookies)
        for user in r.json():
            assert 'password' not in user


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /api/v1/admin/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteUser:
    def test_unauthenticated_returns_401(self, client):
        r = client.delete('/api/v1/admin/users/2')
        assert r.status_code == 401

    def test_regular_user_returns_403(self, client, auth_cookies):
        r = client.delete('/api/v1/admin/users/2', cookies=auth_cookies)
        assert r.status_code == 403

    def test_admin_can_delete_user(self, client, admin_cookies):
        with patch('app.services.auth_service.delete_user_as_admin', return_value=True):
            r = client.delete('/api/v1/admin/users/2', cookies=admin_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_admin_cannot_delete_protected_admin(self, client, admin_cookies):
        """delete_user_as_admin returns False for the default admin user."""
        with patch('app.routers.admin.delete_user_as_admin', return_value=False):
            r = client.delete('/api/v1/admin/users/1', cookies=admin_cookies)
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/admin/stats
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminStats:
    URL = '/api/v1/admin/stats'

    def test_unauthenticated_returns_401(self, client):
        r = client.get(self.URL)
        assert r.status_code == 401

    def test_regular_user_returns_403(self, client, auth_cookies):
        r = client.get(self.URL, cookies=auth_cookies)
        assert r.status_code == 403

    def test_admin_returns_global_stats(self, client, admin_cookies):
        stats = {'total': 50, 'vulns': 12, 'health': 98.0}
        with patch('app.routers.admin.get_stats', return_value=stats):
            r = client.get(self.URL, cookies=admin_cookies)
        assert r.status_code == 200
        data = r.json()
        assert data['total'] == 50

    def test_admin_stats_no_user_id_filter(self, client, admin_cookies):
        """Admin stats endpoint must NOT filter by user_id — it's global."""
        stats = {'total': 50, 'vulns': 12, 'health': 98.0}
        with patch('app.routers.admin.get_stats', return_value=stats) as mock_stats:
            client.get(self.URL, cookies=admin_cookies)
        # Called with no user_id argument (global stats)
        mock_stats.assert_called_once_with()
