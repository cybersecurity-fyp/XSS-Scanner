"""
tests/conftest.py — Shared pytest fixtures for the full test suite.

Layers:
  1. Env vars set before any app import (so config.py doesn't sys.exit).
  2. Session-scoped DB mock that replaces the Supabase client for all tests.
  3. App instance (session-scoped) created once for integration tests.
  4. TestClient fixture (function-scoped) wrapping the shared app.
  5. Session-cookie helpers so integration tests can simulate authenticated users.
"""

import base64
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── 1. Minimal env vars — set BEFORE any app module is imported ───────────────
#    os.environ.setdefault won't override a real .env that's already loaded,
#    but guards against CI / dev environments with no .env file.
os.environ.setdefault('SUPABASE_URL',        'https://test-project.supabase.co')
os.environ.setdefault('SUPABASE_SECRET_KEY', 'test-secret-key-for-ci-testing')
os.environ.setdefault('SESSION_SECRET',      'test-session-secret-for-integration-tests-only')
# Disable SlowAPI rate limiting in tests so repeated calls don't get 429
os.environ['RATELIMIT_ENABLED'] = '0'

# ── 2. Ensure project root is on sys.path ─────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── 3. Shared test-user constants ─────────────────────────────────────────────
TEST_USER  = {'id': 1, 'username': 'testuser', 'email': 'test@example.com',  'role': 'user',  'email_verified': True}
TEST_ADMIN = {'id': 9, 'username': 'admin',    'email': 'admin@example.com', 'role': 'admin', 'email_verified': True}


# ── 4. Session-scoped DB mock ─────────────────────────────────────────────────
_fake_db = MagicMock()


@pytest.fixture(autouse=True, scope='session')
def patch_db():
    """
    Replace the Supabase client with a MagicMock for the entire test session.

    We patch the db in three places because each module that does
      `from app.db.client import db`
    gets its own name-binding at import time.  Patching only app.db.client.db
    doesn't retroactively update those already-bound names.
    """
    with patch('app.db.client.db', _fake_db), \
         patch('app.db.users.db',   _fake_db), \
         patch('app.db.scans.db',   _fake_db):
        yield _fake_db


@pytest.fixture
def db(patch_db):
    """Per-test access to the mock DB; reset call history between tests."""
    patch_db.reset_mock()
    return patch_db


# ── 5. App + TestClient fixtures ──────────────────────────────────────────────

@pytest.fixture(scope='session')
def app(patch_db):
    """Create FastAPI application once for the whole session."""
    from app import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Fresh TestClient per test (cookies are cleared between tests)."""
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── 6. Session cookie helper ──────────────────────────────────────────────────

def make_session_cookie(data: dict, secret_key: str | None = None) -> str:
    """
    Build a Starlette SessionMiddleware-compatible signed cookie value.

    Starlette uses itsdangerous.TimestampSigner over base64(json(session_dict)).
    """
    import itsdangerous
    if secret_key is None:
        from app.config import settings
        secret_key = settings.session_secret
    payload = base64.b64encode(json.dumps(data).encode('utf-8'))
    signer  = itsdangerous.TimestampSigner(secret_key)
    return signer.sign(payload).decode('utf-8')


@pytest.fixture
def auth_cookies():
    """Cookies dict containing a valid session for TEST_USER."""
    return {'xssniper_session': make_session_cookie({'user': TEST_USER})}


@pytest.fixture
def admin_cookies():
    """Cookies dict containing a valid admin session for TEST_ADMIN."""
    return {'xssniper_session': make_session_cookie({'user': TEST_ADMIN})}
