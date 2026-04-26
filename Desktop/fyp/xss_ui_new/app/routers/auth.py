"""app/routers/auth.py — Auth API routes: login, register, logout, OAuth callbacks."""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.dependencies import get_session_user
from app.models.requests import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, ResendVerifyForm
from app.services import auth_service
from app.services import email_service
from app.services import oauth_service

log          = logging.getLogger('xssniper')
router       = APIRouter()
oauth_router = APIRouter()   # registered at /auth — only OAuth callbacks
limiter      = Limiter(key_func=get_remote_address)


@router.post('/login')
@limiter.limit('10/minute')
async def login(form: LoginForm, request: Request):
    result = auth_service.authenticate(form.login, form.password)

    if result is None:
        raise HTTPException(401, 'Invalid credentials')
    if result.get('__locked__'):
        raise HTTPException(429, f"Account locked. Try again in {result['minutes']} minute(s).")
    if result.get('__unverified__'):
        raise HTTPException(403, 'Please verify your email before logging in.')

    request.session.clear()
    request.session['user'] = result
    log.info('Login: %s', result.get('username'))
    return {'success': True, 'user': result}


@router.post('/register')
@limiter.limit('5/minute')
async def register(form: RegisterForm, request: Request):
    if len(form.username) < 3:
        raise HTTPException(400, 'Username must be at least 3 characters')
    if len(form.username) > 32:
        raise HTTPException(400, 'Username must be 32 characters or fewer')
    if not auth_service.is_valid_email(form.email):
        raise HTTPException(400, 'Invalid email address')

    pw_ok, pw_err = auth_service.password_meets_requirements(form.password)
    if not pw_ok:
        raise HTTPException(400, pw_err)
    if form.password != form.confirm:
        raise HTTPException(400, 'Passwords do not match')

    from app.db.users import username_exists, email_exists
    if username_exists(form.username):
        raise HTTPException(400, 'Username already taken')
    if email_exists(form.email):
        raise HTTPException(400, 'Email already registered')

    user_id = auth_service.register_user(form.username, form.email, form.password)
    if not user_id:
        raise HTTPException(500, 'Registration failed')

    if settings.smtp_configured:
        token = auth_service.create_verification_token(user_id)
        sent, err = email_service.send_verification_email(form.email, form.username, token)
        if not sent:
            log.warning('Verification email failed for %s: %s', form.email, err)

    log.info('Registered: %s (%s)', form.username, form.email)
    return {'success': True, 'message': 'Account created! Check your email to verify before logging in.'}


@router.post('/logout')
async def logout(request: Request):
    request.session.clear()
    return {'success': True}


@router.get('/logout')
async def logout_get(request: Request):
    request.session.clear()
    return RedirectResponse('/login')


@router.post('/resend-verification')
@limiter.limit('3/minute')
async def resend_verification(form: ResendVerifyForm, request: Request):
    if not auth_service.is_valid_email(form.email):
        raise HTTPException(400, 'Invalid email address')
    user_id = auth_service.get_unverified_user_id(form.email)
    if user_id and settings.smtp_configured:
        from app.db.users import find_user_by_email
        user    = find_user_by_email(form.email)
        token   = auth_service.create_verification_token(user_id)
        email_service.send_verification_email(form.email, user['username'] if user else 'User', token)
    return {'success': True, 'message': 'If that email is registered and unverified, a new link has been sent.'}


@router.post('/forgot-password')
@limiter.limit('3/minute')
async def forgot_password(form: ForgotPasswordForm, request: Request):
    if not auth_service.is_valid_email(form.email):
        raise HTTPException(400, 'Invalid email address')
    from app.db.users import find_user_by_email
    user = find_user_by_email(form.email)
    if user:
        token     = auth_service.create_password_reset_token(user['id'])
        sent, err = email_service.send_password_reset_email(user['email'], user['username'], token)
        if not sent and settings.smtp_configured:
            raise HTTPException(503, f'Email could not be sent: {err}')
    return {'success': True, 'message': 'If that email is registered, a reset link has been sent.'}


@router.post('/reset-password')
@limiter.limit('10/minute')
async def reset_password(form: ResetPasswordForm, request: Request):
    if not form.token:
        raise HTTPException(400, 'Missing reset token')
    if form.password != form.confirm:
        raise HTTPException(400, 'Passwords do not match')
    pw_ok, pw_err = auth_service.password_meets_requirements(form.password)
    if not pw_ok:
        raise HTTPException(400, pw_err)
    # consume_reset_token verifies token validity and deletes it atomically
    if not auth_service.consume_reset_token(form.token, form.password):
        raise HTTPException(400, 'Reset link is invalid or has expired.')
    return {'success': True, 'message': 'Password updated. You can now log in.'}


# ── OAuth Callbacks (registered on oauth_router, not router) ─────────────────
# These are mounted at /auth/github/callback and /auth/google/callback.
# Keeping them separate prevents login/register/logout from being duplicated
# under /auth when only the OAuth callbacks need that prefix.

@oauth_router.get('/github/callback')
async def github_callback(request: Request, code: str = '', error: str = '', state: str = ''):
    if error or not code:
        return RedirectResponse('/login?error=github_cancelled')

    expected = request.session.pop('oauth_state_github', None)
    if expected and state and state != expected:
        return RedirectResponse('/login?error=github_state_mismatch')

    try:
        token = await oauth_service.exchange_github_code(code)
        if not token:
            return RedirectResponse('/login?error=token_failed')

        profile = await oauth_service.get_github_profile(token)
        if not profile:
            return RedirectResponse('/login?error=profile_failed')

        user_data = oauth_service.get_or_create_github_user(profile)
        request.session.clear()
        request.session['user'] = user_data
        return RedirectResponse('/')
    except Exception:
        log.exception('GitHub OAuth error')
        return RedirectResponse('/login?error=oauth_error')


@oauth_router.get('/google/callback')
async def google_callback(request: Request, code: str = '', error: str = '', state: str = ''):
    if error or not code:
        return RedirectResponse('/login?error=google_cancelled')

    expected = request.session.pop('oauth_state_google', None)
    if expected and state and state != expected:
        return RedirectResponse('/login?error=google_state_mismatch')

    try:
        token = await oauth_service.exchange_google_code(code)
        if not token:
            return RedirectResponse('/login?error=google_token_failed')

        profile = await oauth_service.get_google_profile(token)
        if not profile:
            return RedirectResponse('/login?error=google_profile_failed')
        if not profile.get('email_verified', True):
            return RedirectResponse('/login?error=google_email_not_verified')

        user_data = oauth_service.get_or_create_google_user(profile)
        request.session.clear()
        request.session['user'] = user_data
        return RedirectResponse('/')
    except Exception:
        log.exception('Google OAuth error')
        return RedirectResponse('/login?error=google_error')
