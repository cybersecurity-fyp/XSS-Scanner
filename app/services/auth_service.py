"""
app/services/auth_service.py — Authentication business logic.
Handles password hashing, login, tokens, and account management.
All functions are stateless — DB calls go through app.db.users.
"""

import re
import os
import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.db import users as user_db

_HASH_ITERATIONS = 600_000
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


# ── Password utilities ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, _HASH_ITERATIONS)
    return f'pbkdf2${salt.hex()}${key.hex()}'


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash.startswith('pbkdf2$'):
        return False
    try:
        _, salt_hex, key_hex = stored_hash.split('$')
        salt     = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
        computed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, _HASH_ITERATIONS)
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False


def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def password_meets_requirements(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, 'Password must be at least 8 characters'
    if len(password) > 128:
        return False, 'Password must be 128 characters or fewer'
    if not re.search(r'[A-Z]', password):
        return False, 'Password needs at least one uppercase letter'
    if not re.search(r'[a-z]', password):
        return False, 'Password needs at least one lowercase letter'
    if not re.search(r'[0-9]', password):
        return False, 'Password needs at least one number (0-9)'
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, 'Password needs at least one special character (!@#$...)'
    return True, ''


# ── Authentication ────────────────────────────────────────────────────────────

def authenticate(login: str, password: str) -> Optional[dict]:
    """
    Authenticate by username or email.
    Returns:
      - user dict on success
      - {'__locked__': True, 'minutes': N} if account is locked
      - {'__unverified__': True} if email not verified
      - None on wrong credentials
    """
    row = user_db.find_user_by_login(login)
    if not row:
        return None

    lockout_result = _check_lockout(row)
    if lockout_result is not None:
        return lockout_result

    if not verify_password(password, row['password']):
        _record_failed_attempt(row)
        return None

    if not row.get('email_verified', True):
        return {'__unverified__': True}

    # Success — reset failure counter
    user_db.update_user(row['id'], {'failed_login_attempts': 0, 'locked_until': None})

    return _to_session_user(row)


def _check_lockout(row: dict) -> Optional[dict]:
    locked_until = row.get('locked_until')
    if not locked_until:
        return None
    lu = datetime.fromisoformat(locked_until)
    if lu.tzinfo is None:
        lu = lu.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < lu:
        minutes = int((lu - datetime.now(timezone.utc)).total_seconds() / 60) + 1
        return {'__locked__': True, 'minutes': minutes}
    # Lock expired — clear it
    user_db.update_user(row['id'], {'failed_login_attempts': 0, 'locked_until': None})
    return None


def _record_failed_attempt(row: dict) -> None:
    attempts = (row.get('failed_login_attempts') or 0) + 1
    update = {'failed_login_attempts': attempts}
    if attempts >= _MAX_FAILED_ATTEMPTS:
        locked_until = (datetime.now(timezone.utc) + timedelta(minutes=_LOCKOUT_MINUTES)).isoformat()
        update['locked_until'] = locked_until
    user_db.update_user(row['id'], update)


def _to_session_user(row: dict) -> dict:
    return {
        'id':             row['id'],
        'username':       row['username'],
        'email':          row.get('email', ''),
        'role':           row['role'],
        'email_verified': row.get('email_verified', True),
    }


# ── Registration ──────────────────────────────────────────────────────────────

def register_user(username: str, email: str, password: str) -> Optional[int]:
    return user_db.insert_user(username, email, hash_password(password), email_verified=True)


# ── Email verification ────────────────────────────────────────────────────────

def create_verification_token(user_id: int) -> str:
    token      = secrets.token_urlsafe(48)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    user_db.upsert_verification_token(user_id, token, expires_at)
    return token


def verify_email_token(token: str) -> bool:
    record = user_db.get_verification_token(token)
    if not record:
        return False
    if _is_expired(record['expires_at']):
        user_db.delete_verification_token(token)
        return False
    user_db.update_user(record['user_id'], {'email_verified': True})
    user_db.delete_verification_token(token)
    return True


def get_unverified_user_id(email: str) -> Optional[int]:
    """Return user_id if email is registered and not yet verified."""
    row = user_db.get_unverified_user_by_email(email)
    return row['id'] if row else None


# ── Password reset ────────────────────────────────────────────────────────────

def create_password_reset_token(user_id: int) -> str:
    token      = secrets.token_urlsafe(48)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    user_db.upsert_reset_token(user_id, token, expires_at)
    return token


def verify_reset_token(token: str) -> Optional[dict]:
    record = user_db.get_reset_token(token)
    if not record:
        return None
    if _is_expired(record['expires_at']):
        user_db.delete_reset_token(token)
        return None
    return user_db.find_user_by_id(record['user_id'])


def consume_reset_token(token: str, new_password: str) -> bool:
    user = verify_reset_token(token)
    if not user:
        return False
    user_db.update_user(user['id'], {'password': hash_password(new_password)})
    user_db.delete_reset_token(token)
    return True


# ── Account management ────────────────────────────────────────────────────────

def verify_current_password(user_id: int, password: str) -> bool:
    stored = user_db.get_user_password(user_id)
    if not stored:
        return False
    return verify_password(password, stored)


def update_username(user_id: int, new_username: str) -> tuple[bool, str]:
    if len(new_username) < 3:
        return False, 'Username must be at least 3 characters'
    if len(new_username) > 32:
        return False, 'Username must be 32 characters or fewer'
    if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
        return False, 'Username may only contain letters, numbers and underscores'
    if user_db.user_exists_with_username(new_username, exclude_id=user_id):
        return False, 'Username already taken'
    if user_db.update_user(user_id, {'username': new_username}):
        return True, ''
    return False, 'Failed to update username'


def update_email(user_id: int, new_email: str) -> tuple[bool, str]:
    if not is_valid_email(new_email):
        return False, 'Invalid email address'
    if user_db.user_exists_with_email(new_email, exclude_id=user_id):
        return False, 'Email already registered to another account'
    if user_db.update_user(user_id, {'email': new_email, 'email_verified': False}):
        return True, ''
    return False, 'Failed to update email'


def update_password(user_id: int, new_password: str) -> bool:
    return user_db.update_user(user_id, {'password': hash_password(new_password)})


def delete_own_account(user_id: int, password: str) -> tuple[bool, str]:
    row = user_db.get_user_password_and_role(user_id)
    if not row:
        return False, 'User not found'
    if row['role'] == 'admin':
        return False, 'Admin accounts cannot be self-deleted'
    if not verify_password(password, row['password']):
        return False, 'Incorrect password'
    user_db.delete_user_by_id(user_id)
    return True, ''


def delete_user_as_admin(user_id: int) -> bool:
    username = user_db.find_admin_username(user_id)
    if username == 'admin':
        return False  # Protect the default admin
    return user_db.delete_user_by_id(user_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_expired(expires_at_str: str) -> bool:
    dt = datetime.fromisoformat(expires_at_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > dt
