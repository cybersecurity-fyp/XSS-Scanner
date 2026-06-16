"""
tests/test_db_users.py — Unit tests for app/db/users.py.

The Supabase client (db) is replaced by a MagicMock via the session-scoped
patch_db fixture.  Each test configures the mock to return specific data,
then calls the DB function and asserts on the result.
"""

import pytest
from unittest.mock import MagicMock, patch, call


def _mk_resp(data=None, count=None):
    """Build a mock Supabase response object."""
    r = MagicMock()
    r.data  = data
    r.count = count
    return r


@pytest.fixture
def users(db):
    """Import db module after DB is patched, reset mock, return module."""
    from app.db import users as u
    db.reset_mock()
    return u


# ─────────────────────────────────────────────────────────────────────────────
#  find_user_by_login
# ─────────────────────────────────────────────────────────────────────────────

class TestFindUserByLogin:
    def test_finds_by_username(self, users, db):
        row = {'id': 1, 'username': 'alice', 'email': 'a@b.com',
               'role': 'user', 'password': 'hash', 'email_verified': True,
               'failed_login_attempts': 0, 'locked_until': None}
        db.table.return_value.select.return_value.eq.return_value \
          .limit.return_value.execute.return_value = _mk_resp(data=[row])
        result = users.find_user_by_login('alice')
        assert result == row

    def test_falls_through_to_email(self, users, db):
        # First call (username) returns nothing, second (email) returns row
        row = {'id': 2, 'username': 'bob', 'email': 'bob@example.com',
               'role': 'user', 'password': 'hash', 'email_verified': True,
               'failed_login_attempts': 0, 'locked_until': None}
        empty = _mk_resp(data=[])
        found = _mk_resp(data=[row])
        db.table.return_value.select.return_value.eq.return_value \
          .limit.return_value.execute.side_effect = [empty, found]
        result = users.find_user_by_login('bob@example.com')
        assert result == row

    def test_returns_none_when_not_found(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .limit.return_value.execute.return_value = _mk_resp(data=[])
        result = users.find_user_by_login('nobody')
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
#  find_user_by_email
# ─────────────────────────────────────────────────────────────────────────────

class TestFindUserByEmail:
    def test_returns_user(self, users, db):
        row = {'id': 3, 'username': 'carol', 'email': 'carol@c.com', 'role': 'user'}
        db.table.return_value.select.return_value.eq.return_value \
          .limit.return_value.execute.return_value = _mk_resp(data=[row])
        assert users.find_user_by_email('carol@c.com') == row

    def test_returns_none_when_missing(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .limit.return_value.execute.return_value = _mk_resp(data=[])
        assert users.find_user_by_email('nobody@example.com') is None


# ─────────────────────────────────────────────────────────────────────────────
#  username_exists / email_exists
# ─────────────────────────────────────────────────────────────────────────────

class TestExistenceChecks:
    def test_username_exists_true(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .execute.return_value = _mk_resp(count=1)
        assert users.username_exists('alice') is True

    def test_username_exists_false(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .execute.return_value = _mk_resp(count=0)
        assert users.username_exists('ghost') is False

    def test_email_exists_true(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .execute.return_value = _mk_resp(count=1)
        assert users.email_exists('a@b.com') is True

    def test_email_exists_false(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .execute.return_value = _mk_resp(count=0)
        assert users.email_exists('nobody@b.com') is False


# ─────────────────────────────────────────────────────────────────────────────
#  insert_user
# ─────────────────────────────────────────────────────────────────────────────

class TestInsertUser:
    def test_returns_user_id_on_success(self, users, db):
        db.table.return_value.insert.return_value.execute.return_value = \
            _mk_resp(data=[{'id': 7}])
        result = users.insert_user('newuser', 'new@example.com', 'hashedpw')
        assert result == 7

    def test_returns_none_on_exception(self, users, db):
        db.table.return_value.insert.return_value.execute.side_effect = Exception('DB error')
        result = users.insert_user('baduser', 'bad@example.com', 'hash')
        assert result is None

    def test_returns_none_when_data_empty(self, users, db):
        db.table.return_value.insert.return_value.execute.return_value = _mk_resp(data=[])
        db.table.return_value.select.return_value.eq.return_value \
          .limit.return_value.execute.return_value = _mk_resp(data=[])
        result = users.insert_user('emptyuser', 'empty@e.com', 'hash')
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
#  update_user
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateUser:
    def test_returns_true_on_success(self, users, db):
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        assert users.update_user(1, {'username': 'new_name'}) is True

    def test_returns_false_on_exception(self, users, db):
        db.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception('fail')
        assert users.update_user(1, {'username': 'x'}) is False


# ─────────────────────────────────────────────────────────────────────────────
#  delete_user_by_id
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteUser:
    def test_returns_true_on_success(self, users, db):
        db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        assert users.delete_user_by_id(5) is True

    def test_returns_false_on_exception(self, users, db):
        db.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception('err')
        assert users.delete_user_by_id(5) is False


# ─────────────────────────────────────────────────────────────────────────────
#  get_all_users
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAllUsers:
    def test_returns_formatted_list(self, users, db):
        raw = [
            {'id': 1, 'username': 'admin', 'email': 'a@a.com', 'role': 'admin',
             'email_verified': True, 'created_at': '2026-01-01'},
            {'id': 2, 'username': 'user',  'email': 'u@u.com', 'role': 'user',
             'email_verified': False, 'created_at': '2026-01-02'},
        ]
        db.table.return_value.select.return_value.order.return_value.execute.return_value = \
            _mk_resp(data=raw)
        result = users.get_all_users()
        assert len(result) == 2
        assert result[0]['username'] == 'admin'
        assert 'password' not in result[0]

    def test_returns_empty_list_when_no_users(self, users, db):
        db.table.return_value.select.return_value.order.return_value.execute.return_value = \
            _mk_resp(data=[])
        assert users.get_all_users() == []


# ─────────────────────────────────────────────────────────────────────────────
#  get_preferences / save_preferences
# ─────────────────────────────────────────────────────────────────────────────

class TestPreferences:
    def test_get_preferences_returns_dict(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data={'preferences': {'theme': 'dark'}})
        prefs = users.get_preferences(1)
        assert prefs == {'theme': 'dark'}

    def test_get_preferences_returns_empty_on_exception(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.side_effect = Exception('err')
        assert users.get_preferences(1) == {}

    def test_get_preferences_returns_empty_when_null(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data={'preferences': None})
        assert users.get_preferences(1) == {}

    def test_save_preferences_calls_update_user(self, users, db):
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        result = users.save_preferences(1, {'theme': 'light'})
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
#  Token operations
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenOperations:
    def test_get_verification_token_returns_data(self, users, db):
        tok_data = {'user_id': 5, 'expires_at': '2099-01-01T00:00:00Z'}
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data=tok_data)
        assert users.get_verification_token('sometoken') == tok_data

    def test_get_verification_token_returns_none_on_exception(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.side_effect = Exception('not found')
        assert users.get_verification_token('badtoken') is None

    def test_get_reset_token_returns_data(self, users, db):
        tok_data = {'user_id': 3, 'expires_at': '2099-01-01T00:00:00Z'}
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data=tok_data)
        assert users.get_reset_token('resettoken') == tok_data

    def test_get_reset_token_returns_none_on_exception(self, users, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.side_effect = Exception('not found')
        assert users.get_reset_token('badtoken') is None
