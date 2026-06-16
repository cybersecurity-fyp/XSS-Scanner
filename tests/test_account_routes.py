"""
tests/test_account_routes.py — Integration tests for /api/v1/account/* endpoints.
"""

import pytest
from unittest.mock import patch
from tests.conftest import TEST_USER


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/account/change-password
# ─────────────────────────────────────────────────────────────────────────────

class TestChangePassword:
    URL = '/api/v1/account/change-password'

    VALID = {
        'current_password':  'OldPass@word1',
        'new_password':      'NewPass@word1',
        'confirm_password':  'NewPass@word1',
    }

    def test_unauthenticated_returns_401(self, client):
        r = client.post(self.URL, json=self.VALID)
        assert r.status_code == 401

    def test_password_mismatch_returns_400(self, client, auth_cookies):
        payload = {**self.VALID, 'confirm_password': 'Mismatch@1'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400
        assert 'match' in r.json()['detail'].lower()

    def test_weak_new_password_returns_400(self, client, auth_cookies):
        payload = {**self.VALID, 'new_password': 'weak', 'confirm_password': 'weak'}
        r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_wrong_current_password_returns_400(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=False):
            r = client.post(self.URL, json=self.VALID, cookies=auth_cookies)
        assert r.status_code == 400
        assert 'incorrect' in r.json()['detail'].lower()

    def test_same_password_as_current_returns_400(self, client, auth_cookies):
        payload = {**self.VALID,
                   'new_password':     'OldPass@word1',
                   'confirm_password': 'OldPass@word1'}
        with patch('app.services.auth_service.verify_current_password', return_value=True):
            r = client.post(self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_change_password_success(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=True), \
             patch('app.services.auth_service.update_password', return_value=True):
            r = client.post(self.URL, json=self.VALID, cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_missing_fields_returns_422(self, client, auth_cookies):
        r = client.post(self.URL, json={}, cookies=auth_cookies)
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/account/update-profile
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateProfile:
    URL = '/api/v1/account/update-profile'

    def test_unauthenticated_returns_401(self, client):
        r = client.post(self.URL, json={'field': 'username', 'value': 'x', 'password': 'p'})
        assert r.status_code == 401

    def test_wrong_password_returns_400(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=False):
            r = client.post(self.URL,
                            json={'field': 'username', 'value': 'newname', 'password': 'WrongPass'},
                            cookies=auth_cookies)
        assert r.status_code == 400

    def test_update_username_success(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=True), \
             patch('app.services.auth_service.update_username', return_value=(True, '')):
            r = client.post(self.URL,
                            json={'field': 'username', 'value': 'newname', 'password': 'OldPass@1'},
                            cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_update_email_success(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=True), \
             patch('app.services.auth_service.update_email', return_value=(True, '')), \
             patch('app.routers.account.settings') as mock_settings:
            mock_settings.smtp_configured = False
            r = client.post(self.URL,
                            json={'field': 'email', 'value': 'new@example.com', 'password': 'OldPass@1'},
                            cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_update_invalid_field_returns_400(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=True):
            r = client.post(self.URL,
                            json={'field': 'role', 'value': 'admin', 'password': 'OldPass@1'},
                            cookies=auth_cookies)
        assert r.status_code == 400

    def test_update_username_taken_returns_400(self, client, auth_cookies):
        with patch('app.services.auth_service.verify_current_password', return_value=True), \
             patch('app.services.auth_service.update_username', return_value=(False, 'Username already taken')):
            r = client.post(self.URL,
                            json={'field': 'username', 'value': 'taken', 'password': 'OldPass@1'},
                            cookies=auth_cookies)
        assert r.status_code == 400

    def test_missing_fields_returns_422(self, client, auth_cookies):
        r = client.post(self.URL, json={'field': 'username'}, cookies=auth_cookies)
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /api/v1/account/delete
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteAccount:
    URL = '/api/v1/account/delete'

    VALID = {'password': 'Pass@word1', 'confirm_username': TEST_USER['username']}

    def test_unauthenticated_returns_401(self, client):
        r = client.request('DELETE', self.URL, json=self.VALID)
        assert r.status_code == 401

    def test_wrong_username_confirmation_returns_400(self, client, auth_cookies):
        payload = {**self.VALID, 'confirm_username': 'wronguser'}
        r = client.request('DELETE', self.URL, json=payload, cookies=auth_cookies)
        assert r.status_code == 400

    def test_wrong_password_returns_400(self, client, auth_cookies):
        with patch('app.services.auth_service.delete_own_account',
                   return_value=(False, 'Incorrect password')):
            r = client.request('DELETE', self.URL, json=self.VALID, cookies=auth_cookies)
        assert r.status_code == 400

    def test_delete_success(self, client, auth_cookies):
        with patch('app.services.auth_service.delete_own_account', return_value=(True, '')):
            r = client.request('DELETE', self.URL, json=self.VALID, cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_missing_fields_returns_422(self, client, auth_cookies):
        r = client.request('DELETE', self.URL, json={}, cookies=auth_cookies)
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  GET + POST /api/v1/account/preferences
# ─────────────────────────────────────────────────────────────────────────────

class TestPreferences:
    def test_get_preferences_unauthenticated_returns_401(self, client):
        r = client.get('/api/v1/account/preferences')
        assert r.status_code == 401

    def test_get_preferences_returns_dict(self, client, auth_cookies):
        with patch('app.routers.account.get_preferences', return_value={'theme': 'dark'}):
            r = client.get('/api/v1/account/preferences', cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['theme'] == 'dark'

    def test_save_preferences_unauthenticated_returns_401(self, client):
        r = client.post('/api/v1/account/preferences', json={'theme': 'dark'})
        assert r.status_code == 401

    def test_save_preferences_success(self, client, auth_cookies):
        with patch('app.db.users.save_preferences', return_value=True):
            r = client.post('/api/v1/account/preferences',
                            json={'theme': 'dark', 'notifications': True},
                            cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_save_preferences_invalid_body_returns_400(self, client, auth_cookies):
        r = client.post('/api/v1/account/preferences',
                        content='not-json',
                        headers={'Content-Type': 'application/json'},
                        cookies=auth_cookies)
        assert r.status_code in (400, 422)
