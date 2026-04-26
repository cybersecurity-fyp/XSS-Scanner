"""
tests/test_auth_service.py — Unit tests for app/services/auth_service.py

All DB calls are intercepted by the session-scoped mock in conftest.py.
Pure-computation functions (hashing, validation) need no mocking at all.
"""

import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
#  Password hashing
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordHashing:
    def setup_method(self):
        from app.services.auth_service import hash_password, verify_password
        self.hash_password  = hash_password
        self.verify_password = verify_password

    def test_hash_returns_pbkdf2_prefix(self):
        h = self.hash_password('MyPass@1')
        assert h.startswith('pbkdf2$')

    def test_hash_has_three_parts(self):
        h = self.hash_password('MyPass@1')
        assert len(h.split('$')) == 3

    def test_verify_correct_password(self):
        h = self.hash_password('Correct@99')
        assert self.verify_password('Correct@99', h) is True

    def test_verify_wrong_password(self):
        h = self.hash_password('Correct@99')
        assert self.verify_password('WrongPass@1', h) is False

    def test_two_hashes_of_same_password_are_different(self):
        # Random salt means identical inputs produce different hashes
        h1 = self.hash_password('SamePass@1')
        h2 = self.hash_password('SamePass@1')
        assert h1 != h2
        # But both verify correctly
        assert self.verify_password('SamePass@1', h1) is True
        assert self.verify_password('SamePass@1', h2) is True

    def test_verify_rejects_invalid_hash_format(self):
        assert self.verify_password('anything', 'not_a_valid_hash') is False

    def test_verify_rejects_empty_hash(self):
        assert self.verify_password('anything', '') is False


# ─────────────────────────────────────────────────────────────────────────────
#  Password requirements
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordRequirements:
    def setup_method(self):
        from app.services.auth_service import password_meets_requirements
        self.check = password_meets_requirements

    def test_valid_strong_password(self):
        ok, msg = self.check('StrongPass@1')
        assert ok is True
        assert msg == ''

    def test_too_short(self):
        ok, msg = self.check('Ab@1')
        assert ok is False
        assert '8' in msg

    def test_too_long(self):
        # 133 chars > 128 max; also has uppercase, lowercase, digit, special
        ok, msg = self.check('A' * 130 + 'b@1')
        assert ok is False

    def test_missing_uppercase(self):
        ok, msg = self.check('weakpass@1')
        assert ok is False
        assert 'uppercase' in msg.lower()

    def test_missing_lowercase(self):
        ok, msg = self.check('WEAKPASS@1')
        assert ok is False
        assert 'lowercase' in msg.lower()

    def test_missing_number(self):
        ok, msg = self.check('WeakPass@@')
        assert ok is False
        assert 'number' in msg.lower()

    def test_missing_special_char(self):
        ok, msg = self.check('WeakPass1A')
        assert ok is False
        assert 'special' in msg.lower()


# ─────────────────────────────────────────────────────────────────────────────
#  Email validation
# ─────────────────────────────────────────────────────────────────────────────

class TestEmailValidation:
    def setup_method(self):
        from app.services.auth_service import is_valid_email
        self.check = is_valid_email

    def test_valid_emails(self):
        valid = [
            'user@example.com',
            'user.name+tag@sub.domain.org',
            'a@b.io',
        ]
        for email in valid:
            assert self.check(email) is True, f'{email!r} should be valid'

    def test_invalid_emails(self):
        invalid = [
            'notanemail',
            '@nodomain.com',
            'no@',
            'spaces in@email.com',
            '',
        ]
        for email in invalid:
            assert self.check(email) is False, f'{email!r} should be invalid'


# ─────────────────────────────────────────────────────────────────────────────
#  authenticate() — DB-dependent, uses mock
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthenticate:
    def setup_method(self):
        from app.services import auth_service
        self.auth = auth_service

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

    def test_correct_credentials_returns_user(self):
        row = self._make_user_row()
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            result = self.auth.authenticate('testuser', 'Pass@word1')
        assert result is not None
        assert result['username'] == 'testuser'
        assert 'password' not in result  # password must not leak into session

    def test_wrong_password_returns_none(self):
        row = self._make_user_row()
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            result = self.auth.authenticate('testuser', 'WrongPass@1')
        assert result is None

    def test_unknown_user_returns_none(self):
        with patch('app.db.users.find_user_by_login', return_value=None):
            result = self.auth.authenticate('nobody', 'Pass@word1')
        assert result is None

    def test_locked_account_returns_locked_flag(self):
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        row = self._make_user_row(locked_until=future, failed=5)
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            result = self.auth.authenticate('testuser', 'Pass@word1')
        assert result is not None
        assert result.get('__locked__') is True

    def test_unverified_email_returns_unverified_flag(self):
        row = self._make_user_row(verified=False)
        with patch('app.db.users.find_user_by_login', return_value=row), \
             patch('app.db.users.update_user', return_value=True):
            result = self.auth.authenticate('testuser', 'Pass@word1')
        assert result is not None
        assert result.get('__unverified__') is True


# ─────────────────────────────────────────────────────────────────────────────
#  Token expiry helper
# ─────────────────────────────────────────────────────────────────────────────

class TestIsExpired:
    def setup_method(self):
        from app.services.auth_service import _is_expired
        self.is_expired = _is_expired

    def test_past_timestamp_is_expired(self):
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert self.is_expired(past) is True

    def test_future_timestamp_is_not_expired(self):
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        assert self.is_expired(future) is False

    def test_naive_datetime_treated_as_utc(self):
        from datetime import datetime, timezone, timedelta
        past_naive = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None).isoformat()
        assert self.is_expired(past_naive) is True
