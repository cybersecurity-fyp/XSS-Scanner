"""
tests/test_auth_routes.py — Integration tests for /api/v1/auth/* endpoints.

Every DB call is patched at the function level so no real Supabase is needed.
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import TEST_USER, make_session_cookie


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/auth/login
# ─────────────────────────────────────────────────────────────────────────────

class TestLoginRoute:
    URL = '/api/v1/auth/login'

    def _make_user_row(self, password_plain='Pass@word1', locked_until=None,
                       failed=0, verified=True):
        from app.services.auth_service import hash_password
        return {
            'id':                    42,
            'username':              'testuser',
            'email':                 'test@example.com',
            'role':                  'user',
            'password':              hash_password(password_plain),
            'email_verified':        verified,
            'failed_login_attempts': failed,
            'locked_until':          locked_until,
        }

    def test_login_success_returns_user(self, client):
        row = self._make_user_row()
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post(self.URL, json={'login': 'testuser', 'password': 'Pass@word1'})
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert data['user']['username'] == 'testuser'
        assert 'password' not in data['user']

    def test_login_sets_session_cookie(self, client):
        row = self._make_user_row()
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post(self.URL, json={'login': 'testuser', 'password': 'Pass@word1'})
        assert r.status_code == 200
        assert 'xssniper_session' in r.cookies

    def test_login_wrong_password_returns_401(self, client):
        row = self._make_user_row()
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post(self.URL, json={'login': 'testuser', 'password': 'WrongPass@1'})
        assert r.status_code == 401

    def test_login_unknown_user_returns_401(self, client):
        with patch('app.db.users.find_user_by_login', return_value=None):
            r = client.post(self.URL, json={'login': 'nobody', 'password': 'Pass@word1'})
        assert r.status_code == 401

    def test_login_locked_account_returns_429(self, client):
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        row = self._make_user_row(locked_until=future, failed=5)
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post(self.URL, json={'login': 'testuser', 'password': 'Pass@word1'})
        assert r.status_code == 429

    def test_login_unverified_email_returns_403(self, client):
        row = self._make_user_row(verified=False)
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post(self.URL, json={'login': 'testuser', 'password': 'Pass@word1'})
        assert r.status_code == 403

    def test_login_by_email(self, client):
        row = self._make_user_row()
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            r = client.post(self.URL, json={'login': 'test@example.com', 'password': 'Pass@word1'})
        assert r.status_code == 200

    def test_login_missing_fields_returns_422(self, client):
        r = client.post(self.URL, json={})
        assert r.status_code == 422

    def test_login_login_too_long_returns_422(self, client):
        r = client.post(self.URL, json={'login': 'x' * 300, 'password': 'Pass@word1'})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/auth/register
# ─────────────────────────────────────────────────────────────────────────────

class TestRegisterRoute:
    URL = '/api/v1/auth/register'

    VALID = {
        'username': 'newuser',
        'email':    'new@example.com',
        'password': 'Strong@Pass1',
        'confirm':  'Strong@Pass1',
    }

    def test_register_success(self, client):
        # SMTP is not configured in tests → email sending is skipped automatically
        with patch('app.db.users.username_exists', return_value=False), \
             patch('app.db.users.email_exists',    return_value=False), \
             patch('app.services.auth_service.register_user', return_value=99):
            r = client.post(self.URL, json=self.VALID)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_register_username_too_short(self, client):
        # RegisterForm.username has min_length=3 → Pydantic returns 422
        payload = {**self.VALID, 'username': 'ab'}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 422

    def test_register_username_too_long(self, client):
        payload = {**self.VALID, 'username': 'x' * 40}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 422

    def test_register_invalid_email(self, client):
        payload = {**self.VALID, 'email': 'notanemail'}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 400

    def test_register_weak_password(self, client):
        payload = {**self.VALID, 'password': 'weakpass', 'confirm': 'weakpass'}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 400

    def test_register_password_mismatch(self, client):
        payload = {**self.VALID, 'confirm': 'Different@Pass1'}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 400

    def test_register_duplicate_username(self, client):
        with patch('app.db.users.username_exists', return_value=True), \
             patch('app.db.users.email_exists',    return_value=False):
            r = client.post(self.URL, json=self.VALID)
        assert r.status_code == 400
        assert 'taken' in r.json()['detail'].lower()

    def test_register_duplicate_email(self, client):
        with patch('app.db.users.username_exists', return_value=False), \
             patch('app.db.users.email_exists',    return_value=True):
            r = client.post(self.URL, json=self.VALID)
        assert r.status_code == 400
        assert 'registered' in r.json()['detail'].lower()

    def test_register_missing_fields_returns_422(self, client):
        r = client.post(self.URL, json={'username': 'only'})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  POST + GET /api/v1/auth/logout
# ─────────────────────────────────────────────────────────────────────────────

class TestLogoutRoute:
    def test_logout_post_returns_success(self, client, auth_cookies):
        r = client.post('/api/v1/auth/logout', cookies=auth_cookies)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_logout_get_redirects_to_login(self, client, auth_cookies):
        r = client.get('/api/v1/auth/logout', cookies=auth_cookies,
                       follow_redirects=False)
        assert r.status_code == 307
        assert '/login' in r.headers['location']

    def test_logout_without_session_still_succeeds(self, client):
        r = client.post('/api/v1/auth/logout')
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/auth/forgot-password
# ─────────────────────────────────────────────────────────────────────────────

class TestForgotPasswordRoute:
    URL = '/api/v1/auth/forgot-password'

    def test_forgot_password_known_email(self, client):
        user = {'id': 1, 'username': 'testuser', 'email': 'test@example.com'}
        with patch('app.db.users.find_user_by_email', return_value=user), \
             patch('app.services.auth_service.create_password_reset_token', return_value='tok'), \
             patch('app.services.email_service.send_password_reset_email', return_value=(True, '')):
            r = client.post(self.URL, json={'email': 'test@example.com'})
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_forgot_password_unknown_email_still_returns_200(self, client):
        """Security: never reveal whether an email is registered."""
        with patch('app.db.users.find_user_by_email', return_value=None):
            r = client.post(self.URL, json={'email': 'nobody@example.com'})
        assert r.status_code == 200

    def test_forgot_password_invalid_email_returns_400(self, client):
        r = client.post(self.URL, json={'email': 'notanemail'})
        assert r.status_code == 400

    def test_forgot_password_missing_email_returns_422(self, client):
        r = client.post(self.URL, json={})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/auth/reset-password
# ─────────────────────────────────────────────────────────────────────────────

class TestResetPasswordRoute:
    URL = '/api/v1/auth/reset-password'

    VALID = {
        'token':    'validtoken123',
        'password': 'NewPass@word1',
        'confirm':  'NewPass@word1',
    }

    def test_reset_password_success(self, client):
        with patch('app.services.auth_service.consume_reset_token', return_value=True):
            r = client.post(self.URL, json=self.VALID)
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_reset_password_invalid_token_returns_400(self, client):
        with patch('app.services.auth_service.consume_reset_token', return_value=False):
            r = client.post(self.URL, json=self.VALID)
        assert r.status_code == 400

    def test_reset_password_mismatch_returns_400(self, client):
        payload = {**self.VALID, 'confirm': 'DifferentPass@1'}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 400

    def test_reset_password_weak_password_returns_400(self, client):
        payload = {**self.VALID, 'password': 'weak', 'confirm': 'weak'}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 400

    def test_reset_password_missing_token_returns_400(self, client):
        payload = {**self.VALID, 'token': ''}
        r = client.post(self.URL, json=payload)
        assert r.status_code == 400

    def test_reset_password_missing_fields_returns_422(self, client):
        r = client.post(self.URL, json={'token': 'x'})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/auth/resend-verification
# ─────────────────────────────────────────────────────────────────────────────

class TestResendVerificationRoute:
    URL = '/api/v1/auth/resend-verification'

    def test_resend_verification_valid_email(self, client):
        with patch('app.services.auth_service.get_unverified_user_id', return_value=None):
            r = client.post(self.URL, json={'email': 'user@example.com'})
        assert r.status_code == 200
        assert r.json()['success'] is True

    def test_resend_verification_invalid_email(self, client):
        r = client.post(self.URL, json={'email': 'bad-email'})
        assert r.status_code == 400

    def test_resend_verification_missing_email(self, client):
        r = client.post(self.URL, json={})
        assert r.status_code == 422
