"""
app/services/oauth_service.py — Unified GitHub and Google OAuth2.
Both providers share the same find-or-create user pattern.
"""

import secrets
import urllib.parse
import httpx
from typing import Optional

from app.config import settings
from app.db import users as user_db


# ── GitHub ────────────────────────────────────────────────────────────────────

def get_github_login_url(state: str) -> str:
    params = {
        'client_id':    settings.github_client_id,
        'redirect_uri': settings.github_redirect_uri,
        'scope':        'user:email',
        'state':        state,
    }
    return 'https://github.com/login/oauth/authorize?' + urllib.parse.urlencode(params)


async def exchange_github_code(code: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id':     settings.github_client_id,
                'client_secret': settings.github_client_secret,
                'code':          code,
                'redirect_uri':  settings.github_redirect_uri,
            },
            headers={'Accept': 'application/json'},
        )
        return resp.json().get('access_token')


async def get_github_profile(token: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        resp = await client.get('https://api.github.com/user', headers=headers)
        if resp.status_code != 200:
            return None
        profile = resp.json()

        # Fetch primary email if the profile email is not public
        if not profile.get('email'):
            email_resp = await client.get('https://api.github.com/user/emails', headers=headers)
            emails     = email_resp.json() if email_resp.status_code == 200 else []
            profile['email'] = next((e['email'] for e in emails if e.get('primary')), None)

        return profile


def get_or_create_github_user(profile: dict) -> dict:
    username = profile.get('login', '')
    email    = profile.get('email') or f'{username}@github.user'
    return _find_or_create_oauth_user(username, email, provider='github')


# ── Google ────────────────────────────────────────────────────────────────────

def get_google_login_url(state: str) -> str:
    params = {
        'client_id':     settings.google_client_id,
        'redirect_uri':  settings.google_redirect_uri,
        'response_type': 'code',
        'scope':         'openid email profile',
        'access_type':   'online',
        'prompt':        'select_account',
        'state':         state,
    }
    return 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)


async def exchange_google_code(code: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post('https://oauth2.googleapis.com/token', data={
            'code':          code,
            'client_id':     settings.google_client_id,
            'client_secret': settings.google_client_secret,
            'redirect_uri':  settings.google_redirect_uri,
            'grant_type':    'authorization_code',
        })
        return resp.json().get('access_token')


async def get_google_profile(token: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {token}'},
        )
        return resp.json() if resp.status_code == 200 else None


def get_or_create_google_user(profile: dict) -> dict:
    email    = profile.get('email', '')
    raw_name = profile.get('given_name') or email.split('@')[0]
    username = ''.join(c for c in raw_name if c.isalnum() or c == '_')[:20] or 'user'
    return _find_or_create_oauth_user(username, email, provider='google')


# ── Shared find-or-create logic ───────────────────────────────────────────────

def _find_or_create_oauth_user(username: str, email: str, provider: str) -> dict:
    existing = user_db.find_user_by_email(email)
    if existing:
        return {
            'id':             existing['id'],
            'username':       existing['username'],
            'email':          existing['email'],
            'role':           existing['role'],
            'email_verified': existing.get('email_verified', True),
        }

    # Ensure username is unique (append counter if needed)
    final_username = _unique_username(username)

    # OAuth users get an unguessable sentinel password — they cannot log in via password
    sentinel = f'!oauth-{provider}-{secrets.token_hex(32)}'

    user_id = user_db.insert_user(
        final_username, email, sentinel,
        role='user', email_verified=True,
    )
    return {
        'id':             user_id,
        'username':       final_username,
        'email':          email,
        'role':           'user',
        'email_verified': True,
    }


def _unique_username(base: str) -> str:
    if not user_db.username_exists(base):
        return base
    counter = 1
    while user_db.username_exists(f'{base}{counter}'):
        counter += 1
    return f'{base}{counter}'
