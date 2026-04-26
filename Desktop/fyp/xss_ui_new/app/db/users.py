"""
app/db/users.py — All user table operations.
Pure DB layer: no business logic, no hashing.
"""

from typing import Optional
from app.db.client import db


def find_user_by_login(login: str) -> Optional[dict]:
    """Find user by username or email. Returns full row including password hash."""
    resp = db.table('users').select('*').eq('username', login).limit(1).execute()
    rows = resp.data or []
    if rows:
        return rows[0]
    resp = db.table('users').select('*').eq('email', login).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def find_user_by_email(email: str) -> Optional[dict]:
    resp = db.table('users').select('id, username, email, role').eq('email', email).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def find_user_by_id(user_id: int) -> Optional[dict]:
    resp = db.table('users').select('id, username, email, role').eq('id', user_id).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def username_exists(username: str) -> bool:
    resp = db.table('users').select('id', count='exact').eq('username', username).execute()
    return (resp.count or 0) > 0


def email_exists(email: str) -> bool:
    resp = db.table('users').select('id', count='exact').eq('email', email).execute()
    return (resp.count or 0) > 0


def insert_user(username: str, email: str, password_hash: str,
                role: str = 'user', email_verified: bool = False) -> Optional[int]:
    try:
        resp = db.table('users').insert({
            'username':       username,
            'email':          email,
            'password':       password_hash,
            'role':           role,
            'email_verified': email_verified,
        }).execute()
        rows = resp.data or []
        return rows[0]['id'] if rows else None
    except Exception:
        return None


def update_user(user_id: int, fields: dict) -> bool:
    try:
        db.table('users').update(fields).eq('id', user_id).execute()
        return True
    except Exception:
        return False


def delete_user_by_id(user_id: int) -> bool:
    try:
        db.table('users').delete().eq('id', user_id).execute()
        return True
    except Exception:
        return False


def get_user_password(user_id: int) -> Optional[str]:
    """Return just the password hash for a user, for credential verification."""
    try:
        resp = db.table('users').select('password').eq('id', user_id).single().execute()
        return (resp.data or {}).get('password')
    except Exception:
        return None


def get_user_password_and_role(user_id: int) -> Optional[dict]:
    """Return password hash and role for account deletion checks."""
    try:
        resp = db.table('users').select('password, role').eq('id', user_id).single().execute()
        return resp.data
    except Exception:
        return None


def user_exists_with_username(username: str, exclude_id: int) -> bool:
    """Return True if another user (not exclude_id) already has this username."""
    resp = db.table('users').select('id').eq('username', username).neq('id', exclude_id).limit(1).execute()
    return bool(resp.data)


def user_exists_with_email(email: str, exclude_id: int) -> bool:
    """Return True if another user (not exclude_id) already has this email."""
    resp = db.table('users').select('id').eq('email', email).neq('id', exclude_id).limit(1).execute()
    return bool(resp.data)


def get_unverified_user_by_email(email: str) -> Optional[dict]:
    """Return user row (id) if email is registered and not yet verified, else None."""
    try:
        resp = (
            db.table('users')
            .select('id, email_verified')
            .eq('email', email)
            .eq('email_verified', False)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def find_admin_username(user_id: int) -> Optional[str]:
    """Return username for a user, used to protect the default admin from deletion."""
    try:
        resp = db.table('users').select('username').eq('id', user_id).single().execute()
        return (resp.data or {}).get('username')
    except Exception:
        return None


def get_all_users() -> list[dict]:
    resp = db.table('users').select('*').order('id').execute()
    return [
        {
            'id':             r['id'],
            'username':       r['username'],
            'email':          r.get('email', ''),
            'role':           r['role'],
            'email_verified': r.get('email_verified', False),
        }
        for r in (resp.data or [])
    ]


def get_preferences(user_id: int) -> dict:
    try:
        resp = db.table('users').select('preferences').eq('id', user_id).single().execute()
        return (resp.data or {}).get('preferences') or {}
    except Exception:
        return {}


def save_preferences(user_id: int, prefs: dict) -> bool:
    return update_user(user_id, {'preferences': prefs})


# ── Token tables ──────────────────────────────────────────────────────────────

def upsert_verification_token(user_id: int, token: str, expires_at: str) -> None:
    db.table('email_verifications').delete().eq('user_id', user_id).execute()
    db.table('email_verifications').insert({
        'user_id': user_id, 'token': token, 'expires_at': expires_at,
    }).execute()


def get_verification_token(token: str) -> Optional[dict]:
    try:
        resp = db.table('email_verifications').select('user_id, expires_at').eq('token', token).single().execute()
        return resp.data
    except Exception:
        return None


def delete_verification_token(token: str) -> None:
    db.table('email_verifications').delete().eq('token', token).execute()


def upsert_reset_token(user_id: int, token: str, expires_at: str) -> None:
    db.table('password_resets').delete().eq('user_id', user_id).execute()
    db.table('password_resets').insert({
        'user_id': user_id, 'token': token, 'expires_at': expires_at,
    }).execute()


def get_reset_token(token: str) -> Optional[dict]:
    try:
        resp = db.table('password_resets').select('user_id, expires_at').eq('token', token).single().execute()
        return resp.data
    except Exception:
        return None


def delete_reset_token(token: str) -> None:
    db.table('password_resets').delete().eq('token', token).execute()
